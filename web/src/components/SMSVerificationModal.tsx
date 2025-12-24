'use client';

import { useState, useEffect, useRef } from 'react';
import { MessageSquare, Loader2, CheckCircle, AlertCircle, Phone } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui';
import { api } from '@/lib/api';

interface SMSVerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  phone: string;
}

type Step = 'confirm' | 'request' | 'verify' | 'success' | 'error';

export function SMSVerificationModal({
  isOpen,
  onClose,
  onSuccess,
  phone,
}: SMSVerificationModalProps) {
  const [step, setStep] = useState<Step>('confirm');
  const [code, setCode] = useState(['', '', '', '', '', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionInfo, setSessionInfo] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Countdown timer for resend cooldown
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => {
        setResendCooldown(resendCooldown - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setStep('confirm');
      setCode(['', '', '', '', '', '']);
      setError(null);
      setSessionInfo(null);
      setResendCooldown(0);
    }
  }, [isOpen]);

  const requestSMS = async () => {
    setIsLoading(true);
    setError(null);
    setStep('request');
    try {
      const response = await api.requestBeyondSMS(phone);
      setSessionInfo(response.session_info);
      setStep('verify');
      setResendCooldown(60);
      // Focus first input
      setTimeout(() => inputRefs.current[0]?.focus(), 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao enviar SMS');
      setStep('error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCodeChange = (index: number, value: string) => {
    if (value.length > 1) {
      // Handle paste
      const digits = value.replace(/\D/g, '').slice(0, 6).split('');
      const newCode = [...code];
      digits.forEach((digit, i) => {
        if (index + i < 6) {
          newCode[index + i] = digit;
        }
      });
      setCode(newCode);
      const lastIndex = Math.min(index + digits.length, 5);
      inputRefs.current[lastIndex]?.focus();
    } else {
      const newCode = [...code];
      newCode[index] = value.replace(/\D/g, '');
      setCode(newCode);
      if (value && index < 5) {
        inputRefs.current[index + 1]?.focus();
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !code[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const verifySMS = async () => {
    const fullCode = code.join('');
    if (fullCode.length !== 6) {
      setError('Digite o codigo completo de 6 digitos');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      await api.verifyBeyondSMS(phone, fullCode, sessionInfo || '');
      setStep('success');
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Codigo invalido');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Verificacao Beyond The Club">
      <div className="space-y-6">
        {/* Confirm Step - Show phone as read-only */}
        {step === 'confirm' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageSquare className="h-8 w-8 text-primary-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Vincular conta Beyond The Club
            </h3>
            <p className="text-gray-500 mb-6">
              Enviaremos um SMS para verificar sua conta
            </p>

            {/* Phone display - read only */}
            <div className="flex items-center justify-center gap-3 p-4 bg-gray-50 rounded-lg mb-6">
              <Phone className="h-5 w-5 text-gray-400" />
              <span className="text-lg font-medium text-gray-900">{phone}</span>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg mb-4">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <Button
              variant="primary"
              size="lg"
              className="w-full"
              onClick={requestSMS}
              isLoading={isLoading}
            >
              Enviar SMS
            </Button>
          </div>
        )}

        {/* Request Step */}
        {step === 'request' && (
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageSquare className="h-8 w-8 text-primary-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Enviando SMS...
            </h3>
            <p className="text-gray-500 mb-4">
              Enviando codigo de verificacao para {phone}
            </p>
            {isLoading && (
              <Loader2 className="h-8 w-8 text-primary-600 animate-spin mx-auto" />
            )}
          </div>
        )}

        {/* Verify Step */}
        {step === 'verify' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <MessageSquare className="h-8 w-8 text-primary-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Digite o codigo SMS
            </h3>
            <p className="text-gray-500 mb-6">
              Enviamos um codigo de 6 digitos para {phone}
            </p>

            {/* Code inputs */}
            <div className="flex justify-center gap-2 mb-6">
              {code.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => { inputRefs.current[index] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={digit}
                  onChange={(e) => handleCodeChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  className="w-12 h-14 text-center text-2xl font-bold border-2 border-gray-300 rounded-lg focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:outline-none"
                />
              ))}
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg mb-4">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <Button
              variant="primary"
              size="lg"
              className="w-full"
              onClick={verifySMS}
              isLoading={isLoading}
              disabled={code.join('').length !== 6}
            >
              Verificar
            </Button>

            <button
              onClick={requestSMS}
              className={`mt-4 text-sm ${
                resendCooldown > 0 || isLoading
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'text-primary-600 hover:text-primary-700'
              }`}
              disabled={resendCooldown > 0 || isLoading}
            >
              {resendCooldown > 0
                ? `Reenviar codigo em ${resendCooldown}s`
                : 'Reenviar codigo'}
            </button>
          </div>
        )}

        {/* Success Step */}
        {step === 'success' && (
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Verificado com sucesso!
            </h3>
            <p className="text-gray-500">
              Sua conta Beyond The Club foi vinculada.
            </p>
          </div>
        )}

        {/* Error Step */}
        {step === 'error' && (
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="h-8 w-8 text-red-600" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Erro ao enviar SMS
            </h3>
            <p className="text-gray-500 mb-4">{error}</p>
            <Button variant="primary" onClick={requestSMS}>
              Tentar novamente
            </Button>
          </div>
        )}
      </div>
    </Modal>
  );
}
