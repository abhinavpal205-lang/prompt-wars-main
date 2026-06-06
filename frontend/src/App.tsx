import { useEffect, useRef, useState } from 'react';
import { api } from './api/client';
import styles from './App.module.css';
import { CalmingSession } from './components/CalmingSession';
import { CrisisScreen } from './components/CrisisScreen';
import { Disclaimer } from './components/Disclaimer';
import { FormCheckin } from './components/FormCheckin';
import { ModeSelect } from './components/ModeSelect';
import { ParentSettings } from './components/ParentSettings';
import { ResultCard } from './components/ResultCard';
import { TrendDashboard } from './components/TrendDashboard';
import { VoiceCheckin } from './components/VoiceCheckin';
import type { CheckinResult, ProfileOut } from './types';

type Screen =
  | 'home'
  | 'form'
  | 'voice'
  | 'result'
  | 'crisis'
  | 'dashboard'
  | 'settings'
  | 'calming';

const SCREEN_TITLES: Record<Screen, string> = {
  home: 'Check in',
  form: 'Quick form check-in',
  voice: 'Voice check-in',
  result: 'Your reflection',
  crisis: 'Support right now',
  dashboard: 'Your dashboard',
  settings: 'Settings',
  calming: 'A calming minute',
};

export function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [profileLoaded, setProfileLoaded] = useState(false);
  const mainRef = useRef<HTMLElement>(null);
  const firstRenderRef = useRef(true);

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => {
        setProfileLoaded(true);
      });
  }, []);

  // SPA navigation a11y: announce the new screen via the document title and
  // move focus to the main region (skipped on initial page load).
  useEffect(() => {
    document.title = `${SCREEN_TITLES[screen]} — Sahaay`;
    if (firstRenderRef.current) {
      firstRenderRef.current = false;
      return;
    }
    mainRef.current?.focus();
  }, [screen]);

  const handleResult = (checkin: CheckinResult) => {
    setResult(checkin);
    // The crisis path overrides everything, before any scoring UI.
    setScreen(checkin.crisis ? 'crisis' : 'result');
  };

  const needsOnboarding = profileLoaded && profile !== null && !profile.onboarded;
  const showOnboarding = needsOnboarding && screen !== 'crisis';

  return (
    <div className={styles.shell}>
      <a className="skipLink" href="#main">
        Skip to main content
      </a>
      <header className={styles.header}>
        <button
          type="button"
          className={styles.brand}
          onClick={() => {
            setScreen('home');
          }}
        >
          Sahaay
        </button>
        <nav aria-label="Main">
          {!showOnboarding && (
            <>
              <button
                type="button"
                className={styles.navLink}
                onClick={() => {
                  setScreen('dashboard');
                }}
              >
                Dashboard
              </button>
              <button
                type="button"
                className={styles.navLink}
                onClick={() => {
                  setScreen('settings');
                }}
              >
                Settings
              </button>
            </>
          )}
          <button
            type="button"
            className={styles.crisisLink}
            onClick={() => {
              setScreen('crisis');
            }}
          >
            Need help now?
          </button>
        </nav>
      </header>

      {/* tabIndex -1 lets the skip link and screen changes set focus here */}
      <main id="main" className={styles.main} ref={mainRef} tabIndex={-1}>
        {!profileLoaded && <p role="status">Loading…</p>}

        {profileLoaded && showOnboarding && profile && (
          <>
            <Disclaimer variant="callout" />
            <ParentSettings
              profile={profile}
              intro
              onSaved={(saved) => {
                setProfile(saved);
                setScreen('home');
              }}
            />
          </>
        )}

        {profileLoaded && !showOnboarding && (
          <>
            {screen === 'home' && (
              <ModeSelect
                onVoice={() => {
                  setScreen('voice');
                }}
                onForm={() => {
                  setScreen('form');
                }}
              />
            )}
            {screen === 'form' && <FormCheckin onResult={handleResult} />}
            {screen === 'voice' && (
              <VoiceCheckin
                onResult={handleResult}
                onUseForm={() => {
                  setScreen('form');
                }}
              />
            )}
            {screen === 'result' && result && (
              <ResultCard
                result={result}
                onDone={() => {
                  setScreen('dashboard');
                }}
                onCalm={() => {
                  setScreen('calming');
                }}
              />
            )}
            {screen === 'calming' && result && !result.crisis && (
              <CalmingSession
                band={result.band}
                triggers={result.likely_triggers}
                onDone={() => {
                  setScreen('result');
                }}
                onCrisis={() => {
                  setScreen('crisis');
                }}
              />
            )}
            {screen === 'crisis' && (
              <CrisisScreen
                resources={result?.crisis_resources}
                onBack={() => {
                  setScreen('home');
                }}
              />
            )}
            {screen === 'dashboard' && (
              <TrendDashboard
                onCheckin={() => {
                  setScreen('home');
                }}
              />
            )}
            {screen === 'settings' && profile && (
              <ParentSettings
                profile={profile}
                onSaved={(saved) => {
                  setProfile(saved);
                  setScreen('home');
                }}
              />
            )}
          </>
        )}
      </main>

      <footer className={styles.footer}>
        <Disclaimer variant="footer" />
      </footer>
    </div>
  );
}
