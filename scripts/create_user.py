#!/usr/bin/env python3
"""
Script to create a new user interactively.

Usage:
    # From host (via Docker):
    docker compose exec -it api python scripts/create_user.py

    # Or with phone number as argument:
    docker compose exec -it api python scripts/create_user.py +5511999999999
"""

import argparse
import getpass
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auth.users import UserStore
from src.auth.password import normalize_phone


def main():
    parser = argparse.ArgumentParser(description="Create a new user")
    parser.add_argument("phone", nargs="?", help="Phone number (e.g., +5511999999999)")
    parser.add_argument("--name", "-n", help="User's name")
    parser.add_argument("--email", "-e", help="User's email")
    parser.add_argument("--no-password", action="store_true", help="Create user without password (phone-only auth)")
    args = parser.parse_args()

    store = UserStore()

    # Get phone number
    phone = args.phone
    if not phone:
        phone = input("Phone number (e.g., +5511999999999): ").strip()

    if not phone:
        print("❌ Phone number is required!")
        sys.exit(1)

    # Normalize and validate phone
    normalized = normalize_phone(phone)
    if not normalized:
        print(f"❌ Invalid phone number: {phone}")
        sys.exit(1)

    # Check if user already exists
    existing = store.get_by_phone(normalized)
    if existing:
        print(f"❌ User with phone {normalized} already exists!")
        print(f"   User ID: {existing.user_id}")
        sys.exit(1)

    # Get password
    password = None
    if not args.no_password:
        password = getpass.getpass("Enter password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("❌ Passwords do not match!")
            sys.exit(1)

        if len(password) < 6:
            print("❌ Password must be at least 6 characters!")
            sys.exit(1)

    # Get optional name
    name = args.name
    if not name:
        name = input("Name (optional, press Enter to skip): ").strip() or None

    # Get optional email
    email = args.email
    if not email:
        email = input("Email (optional, press Enter to skip): ").strip() or None

    # Create user
    try:
        user = store.create_user(
            phone=normalized,
            password=password,
            name=name,
            email=email
        )
        print()
        print("✅ User created successfully!")
        print(f"   Phone: {user.phone}")
        print(f"   User ID: {user.user_id}")
        if user.name:
            print(f"   Name: {user.name}")
        if user.email:
            print(f"   Email: {user.email}")
        print(f"   Has password: {'Yes' if user.has_password() else 'No'}")
    except Exception as e:
        print(f"❌ Failed to create user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
