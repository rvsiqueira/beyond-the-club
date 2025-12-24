'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Image from 'next/image';
import { Button } from '@/components/ui';
import { useAuth } from '@/hooks/useAuth';
import { Eye, EyeOff, Phone, Lock, User, AlertCircle } from 'lucide-react';

// Beyond The Club brand colors for the divider
function BrandDivider() {
  return (
    <div className="flex h-1.5 w-full rounded-full overflow-hidden">
      <div className="flex-1 bg-[#1a2744]" />
      <div className="flex-1 bg-[#8b4d5c]" />
      <div className="flex-1 bg-[#d4876c]" />
      <div className="flex-1 bg-[#a8c4b8]" />
    </div>
  );
}

// Inner component that uses useSearchParams
function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, register, isLoading, error } = useAuth();
  const [isRegistering, setIsRegistering] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [form, setForm] = useState({
    phone: '',
    password: '',
    name: '',
  });

  // Check if redirected due to expired token
  useEffect(() => {
    if (searchParams.get('expired') === 'true') {
      setSessionExpired(true);
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSessionExpired(false);
    try {
      if (isRegistering) {
        await register({
          phone: form.phone,
          password: form.password,
          name: form.name || undefined,
        });
      } else {
        await login({
          phone: form.phone,
          password: form.password,
        });
      }
    } catch {
      // Error is handled by useAuth
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 flex">
      {/* Left side - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          {/* Logo */}
          <div className="text-center mb-8">
            <Image
              src="/logo.webp"
              alt="Beyond The Club"
              width={200}
              height={50}
              className="mx-auto mb-6"
            />
            <BrandDivider />
          </div>

          {/* Card */}
          <div className="bg-gray-800 rounded-2xl p-8 shadow-xl border border-gray-700">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-white">
                {isRegistering ? 'Criar conta' : 'Bem-vindo de volta'}
              </h1>
              <p className="text-gray-400 mt-2">
                {isRegistering
                  ? 'Preencha os dados para criar sua conta'
                  : 'Entre com suas credenciais'}
              </p>
            </div>

            {/* Session expired warning */}
            {sessionExpired && (
              <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-500">Sessao expirada</p>
                  <p className="text-xs text-amber-500/80 mt-0.5">
                    Sua sessao expirou. Por favor, faca login novamente.
                  </p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {isRegistering && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Nome
                  </label>
                  <div className="relative">
                    <User className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                    <input
                      type="text"
                      placeholder="Seu nome"
                      value={form.name}
                      onChange={(e) => setForm({ ...form, name: e.target.value })}
                      className="w-full pl-12 pr-4 py-3 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Telefone
                </label>
                <div className="relative">
                  <Phone className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                  <input
                    type="tel"
                    placeholder="+55 11 99999-9999"
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    required
                    className="w-full pl-12 pr-4 py-3 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Senha
                </label>
                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="********"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    required
                    className="w-full pl-12 pr-12 py-3 bg-gray-900 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              <Button
                type="submit"
                className="w-full py-3 text-base font-semibold"
                size="lg"
                isLoading={isLoading}
              >
                {isRegistering ? 'Criar conta' : 'Entrar'}
              </Button>
            </form>

            <div className="mt-8 text-center">
              <button
                type="button"
                onClick={() => {
                  setIsRegistering(!isRegistering);
                  setSessionExpired(false);
                }}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                {isRegistering
                  ? 'Ja tem uma conta? '
                  : 'Nao tem conta? '}
                <span className="text-primary-400 font-medium hover:text-primary-300">
                  {isRegistering ? 'Entrar' : 'Criar uma'}
                </span>
              </button>
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-gray-600 text-sm mt-8">
            Beyond The Club - Surf & Tennis
          </p>
        </div>
      </div>

      {/* Right side - Background image */}
      <div className="hidden lg:block lg:w-1/2 relative">
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900/80 to-gray-900/40 z-10" />
        <Image
          src="/surf-backgrounds/surf-1.jpg"
          alt="Surf"
          fill
          className="object-cover"
          priority
        />
        <div className="absolute inset-0 z-20 flex items-center justify-center p-12">
          <div className="text-center">
            <h2 className="text-4xl font-bold text-white mb-4">
              Gerencie suas sessoes
            </h2>
            <p className="text-xl text-gray-300 max-w-md">
              Acompanhe disponibilidade, gerencie agendamentos e configure preferencias dos membros.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main page component wrapped in Suspense for useSearchParams
export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
