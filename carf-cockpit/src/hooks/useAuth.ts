// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
/**
 * React hook for Firebase authentication.
 *
 * When Firebase is not configured (local dev), returns a mock authenticated
 * state so the app works without login.
 */

import { useCallback, useEffect, useState } from 'react';
import {
    GoogleAuthProvider,
    onAuthStateChanged,
    signInWithPopup,
    signOut as firebaseSignOut,
    type User,
} from 'firebase/auth';
import { firebaseAuth, isFirebaseEnabled } from '../services/firebaseConfig';

export interface AuthState {
    user: User | null;
    loading: boolean;
    isAuthenticated: boolean;
    signIn: () => Promise<void>;
    signOut: () => Promise<void>;
    getToken: () => Promise<string | null>;
}

export function useAuth(): AuthState {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(isFirebaseEnabled);

    useEffect(() => {
        if (!isFirebaseEnabled || !firebaseAuth) {
            setLoading(false);
            return;
        }

        const unsubscribe = onAuthStateChanged(firebaseAuth, (firebaseUser) => {
            setUser(firebaseUser);
            setLoading(false);
        });

        return unsubscribe;
    }, []);

    const signIn = useCallback(async () => {
        if (!firebaseAuth) return;
        const provider = new GoogleAuthProvider();
        await signInWithPopup(firebaseAuth, provider);
    }, []);

    const signOut = useCallback(async () => {
        if (!firebaseAuth) return;
        await firebaseSignOut(firebaseAuth);
    }, []);

    const getToken = useCallback(async (): Promise<string | null> => {
        if (!user) return null;
        return user.getIdToken();
    }, [user]);

    return {
        user,
        loading,
        isAuthenticated: isFirebaseEnabled ? !!user : true,
        signIn,
        signOut,
        getToken,
    };
}
