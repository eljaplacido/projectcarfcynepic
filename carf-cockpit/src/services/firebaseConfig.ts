// Copyright (c) 2026 Cisuregen. Licensed under BSL 1.1 — see LICENSE.
/**
 * Firebase SDK initialization for CARF Cockpit.
 *
 * Reads config from Vite environment variables (VITE_FIREBASE_*).
 * Only initializes when VITE_FIREBASE_API_KEY is set — local dev
 * can skip Firebase entirely.
 */

import { initializeApp, type FirebaseApp } from 'firebase/app';
import { getAuth, type Auth } from 'firebase/auth';

const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
    appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
};

/** True when Firebase is configured via environment variables. */
export const isFirebaseEnabled = !!firebaseConfig.apiKey;

let app: FirebaseApp | null = null;
let auth: Auth | null = null;

if (isFirebaseEnabled) {
    app = initializeApp(firebaseConfig);
    auth = getAuth(app);
}

export { app as firebaseApp, auth as firebaseAuth };
