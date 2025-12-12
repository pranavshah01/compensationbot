'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/lib/store';
import ChatInterface from '@/components/ChatInterface';

export default function ChatPage() {
  const router = useRouter();
  const { isAuthenticated, _hasHydrated } = useAuthStore();

  useEffect(() => {
    // Wait for hydration before checking auth
    if (_hasHydrated && !isAuthenticated) {
      router.push('/');
    }
  }, [isAuthenticated, _hasHydrated, router]);

  // Show loading while hydrating or if not authenticated
  if (!_hasHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
        <div className="animate-spin h-8 w-8 border-4 border-primary-500 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <ChatInterface />;
}




