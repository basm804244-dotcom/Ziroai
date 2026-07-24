'use client';

import { useEffect } from 'react';
import { useUserStore } from '@/store';
import { LandingPage } from '@/components/layout/LandingPage';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

export default function Home() {
  const { isAuthenticated, checkAuth } = useUserStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (!isAuthenticated) {
    return <LandingPage />;
  }

  return <DashboardLayout />;
}
