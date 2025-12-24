"""
Auto-monitor service.

Handles automatic monitoring and booking for members.
"""

import time
import logging
from typing import Optional, List, Dict, Callable

from .base import BaseService, ServiceContext
from .member_service import MemberService
from .availability_service import AvailabilityService
from .booking_service import BookingService
from ..config import SESSION_FIXED_HOURS, get_valid_hours_for_level

logger = logging.getLogger(__name__)


class MonitorService(BaseService):
    """
    Service for automatic monitoring and booking.

    Responsibilities:
    - Run automatic monitoring for selected members
    - Find and book matching slots based on preferences
    - Provide status updates via callbacks
    """

    def __init__(
        self,
        context: ServiceContext,
        member_service: MemberService,
        availability_service: AvailabilityService,
        booking_service: BookingService
    ):
        super().__init__(context)
        self._member_service = member_service
        self._availability_service = availability_service
        self._booking_service = booking_service
        self._running = False
        self._current_monitor_id: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def stop(self):
        """Stop the running monitor."""
        self._running = False
        logger.info("Monitor stop requested")

    def run_auto_monitor(
        self,
        member_ids: List[int],
        target_dates: Optional[List[str]] = None,
        duration_minutes: int = 120,
        check_interval_seconds: int = 30,
        on_status_update: Optional[Callable[[str, str], None]] = None
    ) -> Dict[int, dict]:
        """
        Run automatic monitoring and booking for selected members.

        OPTIMIZED: Only scans availability for each member's preferences,
        not all combinations. Tries to book immediately when slot is found.

        Args:
            member_ids: List of member IDs to monitor (without active bookings)
            target_dates: Optional list of specific dates (None = any date)
            duration_minutes: How long to run the monitor (default: 120 min)
            check_interval_seconds: How often to check (default: 30 sec)
            on_status_update: Optional callback for status updates

        Returns:
            Dict mapping member_id -> booking result (or error info)
        """
        self.require_initialized()

        results = {}
        pending_members = list(member_ids)  # Preserve order
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        self._running = True

        # Helper to log and optionally callback
        def status_update(msg: str, level: str = "info"):
            if level == "info":
                logger.info(msg)
            elif level == "error":
                logger.error(msg)
            elif level == "warning":
                logger.warning(msg)
            if on_status_update:
                on_status_update(msg, level)

        status_update(f"Auto-monitor iniciado para {len(pending_members)} membro(s)")
        status_update(f"Duracao: {duration_minutes} min | Intervalo: {check_interval_seconds}s")
        if target_dates:
            status_update(f"Datas alvo: {', '.join(target_dates)}")
        else:
            status_update("Datas alvo: Qualquer data disponivel")

        check_count = 0
        while pending_members and time.time() < end_time and self._running:
            check_count += 1
            elapsed = int(time.time() - start_time)
            remaining = int((end_time - time.time()) / 60)

            status_update(f"\n=== Check #{check_count} | {elapsed}s decorridos | {remaining} min restantes ===")
            status_update(f"Membros pendentes: {len(pending_members)}")

            # Process each pending member
            members_to_remove = []

            for member_id in pending_members:
                if not self._running:
                    break

                member = self._member_service.get_member_by_id(member_id)
                if not member:
                    status_update(f"Membro {member_id} nao encontrado", "warning")
                    members_to_remove.append(member_id)
                    continue

                prefs = self._member_service.get_member_preferences(member_id, self.current_sport)
                if not prefs or not prefs.sessions:
                    status_update(f"{member.social_name}: Sem preferencias configuradas", "warning")
                    members_to_remove.append(member_id)
                    results[member_id] = {"error": "Sem preferencias configuradas"}
                    continue

                status_update(f"\n{member.social_name}: Buscando slots...")

                # Try each preference in priority order
                booked = False
                for pref_idx, session_pref in enumerate(prefs.sessions, 1):
                    combo_key = session_pref.get_combo_key()
                    status_update(f"  [{pref_idx}/{len(prefs.sessions)}] Verificando {combo_key}...")

                    try:
                        # Fast search for this specific combo
                        slot = self._availability_service.find_slot_for_combo(
                            level=session_pref.level,
                            wave_side=session_pref.wave_side,
                            member_id=member_id,
                            target_dates=target_dates,
                            target_hours=prefs.target_hours
                        )

                        if slot:
                            status_update(f"  Slot encontrado! {slot.date} {slot.interval} ({slot.combo_key})")

                            try:
                                result = self._booking_service.create_booking(slot, member_id)
                                voucher = result.get("voucherCode", "N/A")
                                access = result.get("accessCode", result.get("invitation", {}).get("accessCode", "N/A"))

                                status_update(f"  AGENDADO! Voucher: {voucher} | Access: {access}")

                                results[member_id] = {
                                    "success": True,
                                    "voucher": voucher,
                                    "access_code": access,
                                    "slot": slot.to_dict(),
                                    "member_name": member.social_name
                                }
                                members_to_remove.append(member_id)
                                booked = True
                                break  # Stop checking other preferences

                            except Exception as e:
                                error_msg = str(e)
                                # Check if it's a "already booked" error
                                if "ja possui" in error_msg.lower() or "already" in error_msg.lower():
                                    status_update(f"  Membro ja possui agendamento ativo", "warning")
                                    members_to_remove.append(member_id)
                                    results[member_id] = {"error": "Ja possui agendamento ativo"}
                                    booked = True
                                    break
                                else:
                                    status_update(f"  Erro ao agendar: {e}", "error")
                                    # Continue to next preference
                        else:
                            status_update(f"  Nenhum slot disponivel para {combo_key}")

                    except Exception as e:
                        status_update(f"  Erro ao buscar {combo_key}: {e}", "error")

                if not booked:
                    pref_combos = [s.get_combo_key() for s in prefs.sessions]
                    status_update(f"  Nenhum slot encontrado para preferencias: {pref_combos}")

            # Remove processed members
            for mid in members_to_remove:
                if mid in pending_members:
                    pending_members.remove(mid)

            # Wait before next check
            if pending_members and time.time() < end_time and self._running:
                status_update(f"\nAguardando {check_interval_seconds}s para proximo check...")
                # Sleep in small increments to allow for stop requests
                for _ in range(check_interval_seconds):
                    if not self._running:
                        break
                    time.sleep(1)

        # Final summary
        if not pending_members:
            status_update("\nTodos os membros foram agendados!")
        elif not self._running:
            status_update("\nMonitor interrompido pelo usuario.")
        else:
            remaining_names = []
            for mid in pending_members:
                m = self._member_service.get_member_by_id(mid)
                remaining_names.append(m.social_name if m else str(mid))
            status_update(f"\nTempo esgotado. Membros nao agendados: {', '.join(remaining_names)}")

        self._running = False
        return results

    def run_single_check(
        self,
        member_ids: List[int],
        target_dates: Optional[List[str]] = None,
        auto_book: bool = True
    ) -> Dict[int, dict]:
        """
        Run a single check for all members (no loop).

        Args:
            member_ids: List of member IDs to check
            target_dates: Optional list of specific dates
            auto_book: If True, book immediately when slot found

        Returns:
            Dict mapping member_id -> result info
        """
        self.require_initialized()

        results = {}

        for member_id in member_ids:
            member = self._member_service.get_member_by_id(member_id)
            if not member:
                results[member_id] = {"error": "Member not found"}
                continue

            prefs = self._member_service.get_member_preferences(member_id, self.current_sport)
            if not prefs or not prefs.sessions:
                results[member_id] = {"error": "No preferences configured"}
                continue

            # Try each preference
            for session_pref in prefs.sessions:
                slot = self._availability_service.find_slot_for_combo(
                    level=session_pref.level,
                    wave_side=session_pref.wave_side,
                    member_id=member_id,
                    target_dates=target_dates,
                    target_hours=prefs.target_hours
                )

                if slot:
                    if auto_book:
                        try:
                            result = self._booking_service.create_booking(slot, member_id)
                            results[member_id] = {
                                "success": True,
                                "voucher": result.get("voucherCode"),
                                "access_code": result.get("accessCode"),
                                "slot": slot.to_dict(),
                                "member_name": member.social_name
                            }
                        except Exception as e:
                            results[member_id] = {"error": str(e), "slot_found": slot.to_dict()}
                    else:
                        results[member_id] = {
                            "success": False,
                            "slot_found": slot.to_dict(),
                            "member_name": member.social_name
                        }
                    break
            else:
                results[member_id] = {
                    "success": False,
                    "error": "No matching slot found",
                    "member_name": member.social_name
                }

        return results

    def run_session_search(
        self,
        member_id: int,
        level: str,
        wave_side: str,
        target_date: str,
        target_hour: str,
        auto_book: bool = True,
        duration_minutes: int = 120,
        check_interval_seconds: int = 30,
        on_status_update: Optional[Callable[[str, str], None]] = None
    ) -> Dict:
        """
        Search and optionally book a specific session with fixed parameters.

        Unlike run_auto_monitor which uses member preferences, this method
        allows the user to specify exactly which session they want:
        - Specific level (e.g., "Iniciante2")
        - Specific wave side (e.g., "Lado_esquerdo")
        - Specific date (e.g., "2025-12-26")
        - Specific hour (must be valid for the level)

        Args:
            member_id: Member ID to book for
            level: Session level (Iniciante1, Iniciante2, etc.)
            wave_side: Wave side (Lado_esquerdo or Lado_direito)
            target_date: Target date (YYYY-MM-DD format)
            target_hour: Target hour (HH:MM format, must be valid for level)
            auto_book: If True, book immediately when slot found
            duration_minutes: How long to run the monitor (default: 120 min)
            check_interval_seconds: How often to check (default: 30 sec)
            on_status_update: Optional callback for status updates

        Returns:
            Dict with success/error info and booking details
        """
        self.require_initialized()

        # Helper to log and optionally callback
        def status_update(msg: str, level_type: str = "info"):
            if level_type == "info":
                logger.info(msg)
            elif level_type == "error":
                logger.error(msg)
            elif level_type == "warning":
                logger.warning(msg)
            if on_status_update:
                on_status_update(msg, level_type)

        # Validate level
        valid_hours = get_valid_hours_for_level(level)
        if not valid_hours:
            error_msg = f"Nível inválido: {level}. Níveis válidos: {list(SESSION_FIXED_HOURS.keys())}"
            status_update(error_msg, "error")
            return {"success": False, "error": error_msg}

        # Validate hour for the level
        if target_hour not in valid_hours:
            error_msg = f"Horário {target_hour} inválido para {level}. Horários válidos: {valid_hours}"
            status_update(error_msg, "error")
            return {"success": False, "error": error_msg}

        # Validate wave_side
        valid_sides = ["Lado_esquerdo", "Lado_direito"]
        if wave_side not in valid_sides:
            error_msg = f"Lado inválido: {wave_side}. Lados válidos: {valid_sides}"
            status_update(error_msg, "error")
            return {"success": False, "error": error_msg}

        # Validate member
        member = self._member_service.get_member_by_id(member_id)
        if not member:
            error_msg = f"Membro {member_id} não encontrado"
            status_update(error_msg, "error")
            return {"success": False, "error": error_msg}

        combo_key = f"{level}/{wave_side}"
        status_update(f"Busca de sessão iniciada para {member.social_name}")
        status_update(f"Sessão: {combo_key} | Data: {target_date} | Horário: {target_hour}")

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        self._running = True
        check_count = 0

        while time.time() < end_time and self._running:
            check_count += 1
            elapsed = int(time.time() - start_time)
            remaining = int((end_time - time.time()) / 60)

            status_update(f"\n=== Check #{check_count} | {elapsed}s decorridos | {remaining} min restantes ===")

            try:
                # Search for the specific slot
                slot = self._availability_service.find_slot_for_combo(
                    level=level,
                    wave_side=wave_side,
                    member_id=member_id,
                    target_dates=[target_date],
                    target_hours=[target_hour]
                )

                if slot:
                    # Validate that the slot matches the exact date and hour requested
                    if slot.date != target_date:
                        status_update(f"Slot retornado com data diferente: {slot.date} (esperado: {target_date})", "warning")
                        slot = None
                    elif slot.interval != target_hour:
                        status_update(f"Slot retornado com horário diferente: {slot.interval} (esperado: {target_hour})", "warning")
                        slot = None

                if slot:
                    status_update(f"Slot encontrado! {slot.date} {slot.interval} ({slot.combo_key})")

                    if auto_book:
                        try:
                            result = self._booking_service.create_booking(slot, member_id)
                            voucher = result.get("voucherCode", "N/A")
                            access = result.get("accessCode", result.get("invitation", {}).get("accessCode", "N/A"))

                            status_update(f"AGENDADO! Voucher: {voucher} | Access: {access}")

                            self._running = False
                            return {
                                "success": True,
                                "voucher": voucher,
                                "access_code": access,
                                "slot": slot.to_dict(),
                                "member_name": member.social_name,
                                "member_id": member_id
                            }

                        except Exception as e:
                            error_msg = str(e)
                            if "ja possui" in error_msg.lower() or "already" in error_msg.lower():
                                status_update("Membro já possui agendamento ativo", "warning")
                                self._running = False
                                return {
                                    "success": False,
                                    "error": "Membro já possui agendamento ativo",
                                    "member_name": member.social_name
                                }
                            else:
                                status_update(f"Erro ao agendar: {e}", "error")
                                # Continue searching
                    else:
                        # Slot found but auto_book is disabled
                        status_update("Slot encontrado (auto_book desabilitado)")
                        self._running = False
                        return {
                            "success": True,
                            "booked": False,
                            "slot": slot.to_dict(),
                            "member_name": member.social_name,
                            "member_id": member_id
                        }
                if not slot:
                    status_update(f"Sessão não disponível: {combo_key} | {target_date} | {target_hour}")

            except Exception as e:
                status_update(f"Erro ao buscar slot: {e}", "error")

            # Wait before next check
            if time.time() < end_time and self._running:
                status_update(f"Aguardando {check_interval_seconds}s para próximo check...")
                for _ in range(check_interval_seconds):
                    if not self._running:
                        break
                    time.sleep(1)

        # Timeout or stopped
        if not self._running:
            status_update("Busca interrompida pelo usuário.")
        else:
            status_update(f"Tempo esgotado. Sessão não encontrada: {combo_key} em {target_date} às {target_hour}")

        self._running = False
        return {
            "success": False,
            "error": "Sessão não encontrada no tempo limite",
            "member_name": member.social_name,
            "searched": {
                "level": level,
                "wave_side": wave_side,
                "date": target_date,
                "hour": target_hour
            }
        }

    def get_session_options(self) -> Dict:
        """
        Get available session options with fixed hours.

        Returns:
            Dict with levels, wave_sides, and hours per level
        """
        return {
            "levels": list(SESSION_FIXED_HOURS.keys()),
            "wave_sides": ["Lado_esquerdo", "Lado_direito"],
            "hours_by_level": SESSION_FIXED_HOURS.copy()
        }
