"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
  type User as FirebaseUser,
} from "firebase/auth";
import { ref, onValue } from "firebase/database";
import { getFirebaseAuth, getFirebaseDb } from "@/lib/firebase";

/* ── Types ─────────────────────────────────────────────────────────────────
   Mirrors the RPi User dataclass in app_state.py exactly.
   Password is intentionally omitted — never stored in RTDB.            */

export interface UserProfile {
  username: string;
  email: string;
  phone: string;
  points: number;
  is_guest: boolean;
}

interface AuthContextType {
  firebaseUser: FirebaseUser | null;
  userProfile: UserProfile | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* ── Auth state + real-time profile listener ─────────────────────────
     When Firebase Auth resolves a user, subscribe to /users/{uid} for
     live credit balance updates pushed by the RPi kiosk.              */
  useEffect(() => {
    const unsubscribeAuth = onAuthStateChanged(getFirebaseAuth(), (user) => {
      setFirebaseUser(user);
      if (!user) {
        setUserProfile(null);
        setLoading(false);
      }
    });
    return unsubscribeAuth;
  }, []);

  useEffect(() => {
    if (!firebaseUser) return;

    // Load /users/{uid} — the path created by the RPi during kiosk registration
    const userRef = ref(getFirebaseDb(), `users/${firebaseUser.uid}`);
    const unsubscribeDb = onValue(userRef, (snap) => {
      if (snap.exists()) {
        setUserProfile(snap.val() as UserProfile);
      } else {
        // Firebase Auth succeeded but no RTDB profile yet (kiosk registration pending)
        setUserProfile(null);
      }
      setLoading(false);
    });

    return () => unsubscribeDb();
  }, [firebaseUser]);

  /* ── Actions ─────────────────────────────────────────────────────────── */

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      await signInWithEmailAndPassword(getFirebaseAuth(), email, password);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    await signOut(getFirebaseAuth());
    setUserProfile(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{
        firebaseUser,
        userProfile,
        loading,
        error,
        login,
        logout,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
