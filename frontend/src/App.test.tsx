import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

// Firebase initializes at import time and talks to the network, so stub the
// whole layer. onAuthStateChanged immediately reports "logged out".
vi.mock('./firebase', () => ({ auth: {}, db: {} }));

vi.mock('firebase/auth', () => ({
  onAuthStateChanged: (_auth: unknown, cb: (user: null) => void) => {
    cb(null);
    return () => {};
  },
  signInWithPopup: vi.fn(),
  GoogleAuthProvider: class {},
}));

vi.mock('firebase/firestore', () => ({
  doc: vi.fn(),
  setDoc: vi.fn(),
  getDoc: vi.fn(),
  collection: vi.fn(),
  addDoc: vi.fn(),
  query: vi.fn(),
  where: vi.fn(),
  onSnapshot: vi.fn(() => () => {}),
  Timestamp: {},
  getDocFromServer: vi.fn(),
}));

import App from './App';

describe('App smoke test', () => {
  it('renders the sign-in screen when logged out', async () => {
    render(<App />);

    expect(await screen.findByText('NutriLive AI')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /get started/i })).toBeInTheDocument();
  });
});
