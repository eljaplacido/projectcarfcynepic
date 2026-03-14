// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
import React from 'react';
import { useAuth } from '../../hooks/useAuth';
import { isFirebaseEnabled } from '../../services/firebaseConfig';
import LoginPage from './LoginPage';

interface AuthGuardProps {
    children: React.ReactNode;
}

/**
 * Wraps children with authentication check.
 *
 * - When Firebase is not configured (local dev): renders children immediately.
 * - When Firebase is configured: shows LoginPage until user authenticates.
 */
const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
    const { user, loading, signIn } = useAuth();

    // Local dev — no Firebase, skip auth entirely
    if (!isFirebaseEnabled) {
        return <>{children}</>;
    }

    // Loading Firebase auth state
    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
                <div className="text-center">
                    <svg className="animate-spin h-10 w-10 text-blue-400 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    <p className="text-slate-400 text-sm">Loading...</p>
                </div>
            </div>
        );
    }

    // Not authenticated — show login page
    if (!user) {
        return <LoginPage onSignIn={signIn} />;
    }

    // Authenticated — render the app
    return <>{children}</>;
};

export default AuthGuard;
