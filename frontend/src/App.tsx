import React, { useState, useEffect, useRef, useMemo, Component, ErrorInfo, ReactNode } from 'react';

// --- Error Boundary ---
class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean, error: any }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-full flex flex-col items-center justify-center p-8 text-center bg-[#FDF8F8]">
          <h2 className="text-xl font-bold mb-4">Something went wrong</h2>
          <pre className="text-xs bg-gray-100 p-4 rounded-lg overflow-auto max-w-full mb-6">
            {this.state.error?.message || "Unknown error"}
          </pre>
          <button 
            onClick={() => window.location.reload()}
            className="bg-black text-white px-6 py-3 rounded-xl font-bold"
          >
            Reload App
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ... rest of the file ...
import { 
  Mic, 
  Plus, 
  Calendar, 
  CircleUser, 
  LayoutDashboard, 
  Activity, 
  Sparkles,
  X,
  Check,
  ChevronLeft,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { format, addDays, startOfToday, isSameDay } from 'date-fns';
import { cn } from './lib/utils';
import { auth, db } from './firebase';
import { 
  signInWithPopup, 
  GoogleAuthProvider, 
  onAuthStateChanged,
  User as FirebaseUser
} from 'firebase/auth';
import { 
  doc, 
  setDoc, 
  getDoc, 
  collection, 
  addDoc, 
  query, 
  where, 
  onSnapshot,
  Timestamp,
  getDocFromServer
} from 'firebase/firestore';
import { UserProfile, Meal, DailyStats } from './types';

const BACKEND_URL = (import.meta as any).env?.VITE_BACKEND_URL || 'http://localhost:8000';

// --- Constants & Types ---
const CALORIE_GOAL = 1500;
const MACRO_GOALS = {
  protein: 95,
  carbs: 200,
  fat: 50,
  fiber: 25
};

// --- Components ---

const MacroCard = ({ label, value, goal, unit = 'g', color = 'bg-black' }: { 
  label: string; 
  value: number; 
  goal: number; 
  unit?: string;
  color?: string;
}) => {
  const percentage = Math.min((value / goal) * 100, 100);
  
  return (
    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col gap-2">
      <div className="flex justify-between items-end">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400">{label}</p>
          <p className="text-xl font-bold leading-tight">
            {value}<span className="text-sm font-medium text-gray-400 ml-0.5">{unit}</span>
          </p>
        </div>
        <p className="text-[10px] font-medium text-gray-300 mb-1">{goal}{unit}</p>
      </div>
      <div className="h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          className={cn("h-full rounded-full", color)}
        />
      </div>
    </div>
  );
};

const VoiceVisualizer = ({ isListening }: { isListening: boolean }) => {
  return (
    <div className="flex items-center justify-center gap-1 h-8">
      {[...Array(12)].map((_, i) => (
        <motion.div
          key={i}
          animate={isListening ? {
            height: [4, Math.random() * 24 + 4, 4],
          } : { height: 4 }}
          transition={{
            repeat: Infinity,
            duration: 0.5 + Math.random() * 0.5,
            ease: "easeInOut"
          }}
          className="w-1 bg-black rounded-full"
        />
      ))}
    </div>
  );
};

// --- Main App ---

export default function App() {
  return (
    <ErrorBoundary>
      <NutriLiveApp />
    </ErrorBoundary>
  );
}

// --- Error Handling ---
enum OperationType {
  CREATE = 'create',
  UPDATE = 'update',
  DELETE = 'delete',
  LIST = 'list',
  GET = 'get',
  WRITE = 'write',
}

interface FirestoreErrorInfo {
  error: string;
  operationType: OperationType;
  path: string | null;
  authInfo: {
    userId?: string;
    email?: string | null;
    emailVerified?: boolean;
    isAnonymous?: boolean;
    tenantId?: string | null;
    providerInfo?: any[];
  }
}

function handleFirestoreError(error: unknown, operationType: OperationType, path: string | null) {
  const errInfo: FirestoreErrorInfo = {
    error: error instanceof Error ? error.message : String(error),
    authInfo: {
      userId: auth.currentUser?.uid,
      email: auth.currentUser?.email,
      emailVerified: auth.currentUser?.emailVerified,
      isAnonymous: auth.currentUser?.isAnonymous,
      tenantId: auth.currentUser?.tenantId,
      providerInfo: auth.currentUser?.providerData.map(provider => ({
        providerId: provider.providerId,
        displayName: provider.displayName,
        email: provider.email,
        photoUrl: provider.photoURL
      })) || []
    },
    operationType,
    path
  }
  console.error('Firestore Error: ', JSON.stringify(errInfo));
  throw new Error(JSON.stringify(errInfo));
}

function NutriLiveApp() {
  const [user, setUser] = useState<FirebaseUser | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [selectedDate, setSelectedDate] = useState(startOfToday());
  const [isLiveModalOpen, setIsLiveModalOpen] = useState(false);
  const [isLoggingMeal, setIsLoggingMeal] = useState(false);
  const [pendingMeal, setPendingMeal] = useState<Partial<Meal> | null>(null);
  const [isAuthReady, setIsAuthReady] = useState(false);

  // --- Firebase Logic ---

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setIsAuthReady(true);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (!user) return;

    const userDocRef = doc(db, 'users', user.uid);
    const unsubscribeProfile = onSnapshot(userDocRef, (docSnap) => {
      if (docSnap.exists()) {
        setProfile(docSnap.data() as UserProfile);
      } else {
        const defaultProfile: UserProfile = {
          displayName: user.displayName || 'User',
          calorieGoal: CALORIE_GOAL,
          proteinGoal: MACRO_GOALS.protein,
          carbsGoal: MACRO_GOALS.carbs,
          fatGoal: MACRO_GOALS.fat,
          fiberGoal: MACRO_GOALS.fiber
        };
        setDoc(userDocRef, defaultProfile).catch(e => handleFirestoreError(e, OperationType.WRITE, `users/${user.uid}`));
      }
    }, (e) => handleFirestoreError(e, OperationType.GET, `users/${user.uid}`));

    const mealsQuery = query(
      collection(db, 'users', user.uid, 'meals'),
      where('timestamp', '>=', format(selectedDate, 'yyyy-MM-dd')),
      where('timestamp', '<', format(addDays(selectedDate, 1), 'yyyy-MM-dd'))
    );

    const unsubscribeMeals = onSnapshot(mealsQuery, (snapshot) => {
      const fetchedMeals = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() } as Meal));
      setMeals(fetchedMeals);
    }, (e) => handleFirestoreError(e, OperationType.LIST, `users/${user.uid}/meals`));

    return () => {
      unsubscribeProfile();
      unsubscribeMeals();
    };
  }, [user, selectedDate]);

  const handleLogin = async () => {
    const provider = new GoogleAuthProvider();
    try {
      await signInWithPopup(auth, provider);
    } catch (error) {
      console.error("Login failed", error);
    }
  };

  const dailyStats = useMemo(() => {
    return meals.reduce((acc, meal) => ({
      calories: acc.calories + meal.calories,
      protein: acc.protein + meal.protein,
      carbs: acc.carbs + meal.carbs,
      fat: acc.fat + meal.fat,
      fiber: acc.fiber + meal.fiber
    }), { calories: 0, protein: 0, carbs: 0, fat: 0, fiber: 0 });
  }, [meals]);

  // --- Gemini Live Logic ---
  const [isGeminiListening, setIsGeminiListening] = useState(false);
  const [chatHistory, setChatHistory] = useState<{ role: 'user' | 'model', text: string, isFinished?: boolean }[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const nextPlaybackTimeRef = useRef<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startLiveSession = async () => {
    setIsLiveModalOpen(true);
    setIsGeminiListening(true);
    setChatHistory([]);
    nextPlaybackTimeRef.current = 0;
    audioSourcesRef.current.forEach(s => { try { s.stop(); } catch (e) {} });
    audioSourcesRef.current = [];

    // Initialize playback context on user gesture
    playbackContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });

    try {
      const created = await fetch(`${BACKEND_URL}/v1/live/session`, { method: 'POST' });
      const { session_id } = await created.json();
      const wsScheme = BACKEND_URL.startsWith('https') ? 'wss' : 'ws';
      const wsHost = BACKEND_URL.replace(/^https?:\/\//, '');
      const ws = new WebSocket(`${wsScheme}://${wsHost}/v1/live/ws/${session_id}`);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'start' }));
        startAudioStreaming(ws);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === 'tool_call' && message.name === 'prepare_meal_log') {
          setPendingMeal({
            ...message.args,
            timestamp: new Date().toISOString(),
          });
          setIsLoggingMeal(true);
          stopLiveSession();
          return;
        }
        if (message.type === 'model_transcript' && message.text) {
          setChatHistory(prev => {
            const newHistory = [...prev];
            const lastMsg = newHistory[newHistory.length - 1];
            if (lastMsg && lastMsg.role === 'model' && !lastMsg.isFinished) {
              lastMsg.text = message.text;
              if (message.finished) lastMsg.isFinished = true;
            } else {
              newHistory.push({ role: 'model', text: message.text, isFinished: message.finished });
            }
            return newHistory;
          });
        }
        if (message.type === 'user_transcript' && message.text) {
          setChatHistory(prev => {
            const newHistory = [...prev];
            const lastMsg = newHistory[newHistory.length - 1];
            if (lastMsg && lastMsg.role === 'user' && !lastMsg.isFinished) {
              lastMsg.text = message.text;
              if (message.finished) lastMsg.isFinished = true;
            } else {
              newHistory.push({ role: 'user', text: message.text, isFinished: message.finished });
            }
            return newHistory;
          });
        }
        if (message.type === 'model_audio_chunk' && message.audio?.data) {
          playAudio(message.audio.data);
        }
      };

      ws.onclose = () => {
        stopAudioStreaming();
      };
    } catch (error) {
      console.error("Failed to connect to Gemini Live", error);
    }
  };

  const stopLiveSession = () => {
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsLiveModalOpen(false);
    setIsGeminiListening(false);
    stopAudioStreaming();
    audioSourcesRef.current.forEach(s => { try { s.stop(); } catch (e) {} });
    audioSourcesRef.current = [];
  };

  const startAudioStreaming = async (ws: WebSocket) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          sampleRate: 16000,
        } 
      });
      streamRef.current = stream;
      
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
        }
        
        const base64Data = btoa(String.fromCharCode(...new Uint8Array(pcmData.buffer)));
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'audio_chunk',
            audio: { data: base64Data, mime_type: 'audio/pcm;rate=16000' }
          }));
        }
      };
    } catch (error) {
      console.error("Microphone access denied", error);
    }
  };

  const stopAudioStreaming = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }
  };

  const audioSourcesRef = useRef<AudioBufferSourceNode[]>([]);

  const playAudio = (base64Data: string) => {
    const binary = atob(base64Data);
    const bytes = new Int16Array(binary.length / 2);
    for (let i = 0; i < bytes.length; i++) {
      bytes[i] = (binary.charCodeAt(i * 2) & 0xFF) | (binary.charCodeAt(i * 2 + 1) << 8);
    }
    
    const audioContext = playbackContextRef.current;
    if (!audioContext) return;
    
    const buffer = audioContext.createBuffer(1, bytes.length, 24000);
    const channelData = buffer.getChannelData(0);
    for (let i = 0; i < bytes.length; i++) {
      channelData[i] = bytes[i] / 0x7FFF;
    }
    
    const source = audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.destination);
    
    const currentTime = audioContext.currentTime;
    const playTime = Math.max(currentTime, nextPlaybackTimeRef.current);
    source.start(playTime);
    nextPlaybackTimeRef.current = playTime + buffer.duration;

    audioSourcesRef.current.push(source);
    source.onended = () => {
      audioSourcesRef.current = audioSourcesRef.current.filter(s => s !== source);
    };
  };

  const saveMeal = async () => {
    if (!user || !pendingMeal) return;
    try {
      await addDoc(collection(db, 'users', user.uid, 'meals'), pendingMeal);
      setIsLoggingMeal(false);
      setPendingMeal(null);
    } catch (error) {
      handleFirestoreError(error, OperationType.WRITE, `users/${user.uid}/meals`);
    }
  };

  // --- UI Render ---

  if (!isAuthReady) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-[#FDF8F8]">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="h-screen w-full flex flex-col items-center justify-center bg-[#FDF8F8] p-8 text-center">
        <div className="w-20 h-20 bg-black rounded-3xl flex items-center justify-center mb-6 shadow-xl">
          <Sparkles className="text-white w-10 h-10" />
        </div>
        <h1 className="text-3xl font-bold mb-2">NutriLive AI</h1>
        <p className="text-gray-500 mb-8 max-w-xs">Track your nutrition with the power of real-time voice AI.</p>
        <button 
          onClick={handleLogin}
          className="w-full max-w-xs bg-black text-white py-4 rounded-2xl font-bold shadow-lg active:scale-95 transition-transform"
        >
          Get Started
        </button>
      </div>
    );
  }

  const calendarDays = [...Array(7)].map((_, i) => addDays(startOfToday(), i - 6));

  return (
    <div className="h-screen w-full bg-[#FDF8F8] flex flex-col overflow-hidden font-sans text-gray-900">
      {/* Header */}
      <header className="px-6 pt-12 pb-4">
        <div className="flex justify-between items-center mb-6">
          <div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">
              {format(selectedDate, 'MMM yyyy')}
            </p>
            <h1 className="text-2xl font-bold">Good afternoon, {profile?.displayName?.split(' ')[0]}</h1>
          </div>
          <div className="w-10 h-10 rounded-full bg-gray-200 overflow-hidden border-2 border-white shadow-sm">
            <img src={user.photoURL || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.uid}`} alt="Profile" />
          </div>
        </div>

        {/* Calendar Strip */}
        <div className="flex justify-between items-center gap-2 overflow-x-auto no-scrollbar pb-2">
          {calendarDays.map((day, i) => {
            const isSelected = isSameDay(day, selectedDate);
            return (
              <button
                key={i}
                onClick={() => setSelectedDate(day)}
                className={cn(
                  "flex flex-col items-center min-w-[44px] py-3 rounded-2xl transition-all",
                  isSelected ? "bg-black text-white shadow-lg scale-105" : "bg-transparent text-gray-400"
                )}
              >
                <span className="text-[10px] font-bold uppercase mb-1">{format(day, 'EEE')}</span>
                <span className="text-sm font-bold">{format(day, 'd')}</span>
                {isSelected && <div className="w-1 h-1 bg-white rounded-full mt-1" />}
              </button>
            );
          })}
        </div>
      </header>

      {/* Dashboard Content */}
      <main className="flex-1 overflow-y-auto px-6 pb-32 no-scrollbar">
        {/* Calorie Circle */}
        <div className="flex flex-col items-center justify-center py-8 relative">
          <div className="relative w-64 h-64 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90">
              <circle
                cx="128"
                cy="128"
                r="110"
                fill="none"
                stroke="#F3F4F6"
                strokeWidth="12"
              />
              <motion.circle
                cx="128"
                cy="128"
                r="110"
                fill="none"
                stroke="black"
                strokeWidth="12"
                strokeDasharray={2 * Math.PI * 110}
                initial={{ strokeDashoffset: 2 * Math.PI * 110 }}
                animate={{ strokeDashoffset: 2 * Math.PI * 110 * (1 - dailyStats.calories / CALORIE_GOAL) }}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-5xl font-black">{dailyStats.calories}</span>
              <span className="text-sm font-bold text-gray-400">of {CALORIE_GOAL} kcal</span>
            </div>
          </div>
          <p className="mt-4 text-sm font-bold text-gray-400">
            {Math.max(CALORIE_GOAL - dailyStats.calories, 0)} remaining
          </p>
        </div>

        {/* Macros Grid */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <MacroCard label="Protein" value={dailyStats.protein} goal={MACRO_GOALS.protein} color="bg-black" />
          <MacroCard label="Carbs" value={dailyStats.carbs} goal={MACRO_GOALS.carbs} color="bg-black" />
          <MacroCard label="Fat" value={dailyStats.fat} goal={MACRO_GOALS.fat} color="bg-black" />
          <MacroCard label="Fiber" value={dailyStats.fiber} goal={MACRO_GOALS.fiber} color="bg-green-500" />
        </div>
      </main>

      {/* Bottom Navigation */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-xl border-t border-gray-100 px-8 py-6 flex justify-between items-center z-40">
        <button className="flex flex-col items-center gap-1 text-black">
          <LayoutDashboard className="w-6 h-6" />
          <span className="text-[10px] font-bold uppercase">Today</span>
        </button>
        <button className="flex flex-col items-center gap-1 text-gray-300">
          <Activity className="w-6 h-6" />
          <span className="text-[10px] font-bold uppercase">Cycle</span>
        </button>
        
        {/* Voice Trigger FAB */}
        <div className="absolute -top-10 left-1/2 -translate-x-1/2">
          <button 
            onClick={startLiveSession}
            className="w-20 h-20 bg-black rounded-full flex items-center justify-center shadow-2xl active:scale-90 transition-transform border-4 border-[#FDF8F8]"
          >
            <Mic className="text-white w-8 h-8" />
          </button>
        </div>

        <button className="flex flex-col items-center gap-1 text-gray-300">
          <Sparkles className="w-6 h-6" />
          <span className="text-[10px] font-bold uppercase">Wellness</span>
        </button>
        <button className="flex flex-col items-center gap-1 text-gray-300">
          <CircleUser className="w-6 h-6" />
          <span className="text-[10px] font-bold uppercase">Skin</span>
        </button>
      </nav>

      {/* Gemini Live Modal */}
      <AnimatePresence>
        {isLiveModalOpen && (
          <motion.div 
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-0 z-50 bg-white flex flex-col"
          >
            <div className="p-6 flex justify-between items-center border-b border-gray-50">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs font-bold uppercase tracking-widest text-gray-400">
                  {isGeminiListening ? "Gemini Speaking..." : "Listening..."}
                </span>
              </div>
              <button onClick={stopLiveSession} className="p-2 hover:bg-gray-100 rounded-full">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6 no-scrollbar">
              {chatHistory.length === 0 && (
                <div className="flex-1 flex flex-col items-center justify-center text-center opacity-40">
                  <Sparkles className="w-12 h-12 mb-4" />
                  <p className="text-lg font-medium">Just speak naturally</p>
                  <p className="text-sm italic">"I had dal and rice for lunch"</p>
                </div>
              )}
              {chatHistory.map((chat, i) => (
                <motion.div 
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    "max-w-[85%] p-4 rounded-2xl",
                    chat.role === 'user' ? "bg-black text-white self-end" : "bg-gray-100 text-black self-start"
                  )}
                >
                  <p className="text-sm leading-relaxed">{chat.text}</p>
                </motion.div>
              ))}
            </div>

            <div className="p-8 bg-gray-50/50 border-t border-gray-100 flex flex-col items-center gap-6">
              <VoiceVisualizer isListening={isGeminiListening} />
              <button 
                onClick={stopLiveSession}
                className="text-sm font-bold text-gray-400 uppercase tracking-widest"
              >
                Close
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Meal Confirmation Modal */}
      <AnimatePresence>
        {isLoggingMeal && pendingMeal && (
          <div className="fixed inset-0 z-[60] flex items-end justify-center p-4 bg-black/20 backdrop-blur-sm">
            <motion.div 
              initial={{ y: 100, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="w-full max-w-md bg-white rounded-[32px] p-8 shadow-2xl"
            >
              <div className="flex flex-col gap-6">
                <div>
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Ready to log</p>
                  <h2 className="text-xl font-bold leading-tight">
                    Logged {pendingMeal.name} for {pendingMeal.type}.
                  </h2>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between items-center py-2 border-b border-gray-50">
                    <span className="text-sm font-medium text-gray-500 capitalize">{pendingMeal.name}</span>
                    <div className="text-right">
                      <p className="text-sm font-bold">{pendingMeal.calories} cal</p>
                      <p className="text-[10px] text-gray-400">{pendingMeal.protein}g P</p>
                    </div>
                  </div>
                  <div className="flex justify-between items-center pt-2">
                    <span className="text-sm font-bold uppercase tracking-wider">Total ({pendingMeal.type})</span>
                    <div className="text-right">
                      <p className="text-lg font-black">{pendingMeal.calories} cal</p>
                      <p className="text-xs font-bold text-gray-400">{pendingMeal.protein}g P</p>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 pt-2">
                  <button 
                    onClick={() => { setIsLoggingMeal(false); setPendingMeal(null); }}
                    className="flex-1 py-4 rounded-2xl font-bold text-gray-400 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button 
                    onClick={saveMeal}
                    className="flex-[2] bg-black text-white py-4 rounded-2xl font-bold shadow-lg active:scale-95 transition-transform flex items-center justify-center gap-2"
                  >
                    <Check className="w-5 h-5" />
                    Log Meal
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
