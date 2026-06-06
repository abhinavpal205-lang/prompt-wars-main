import { useEffect, useState } from 'react';
import { api } from './api/client';
import styles from './App.module.css';
import { CrisisScreen } from './components/CrisisScreen';
import { Disclaimer } from './components/Disclaimer';
import { FormCheckin } from './components/FormCheckin';
import { ModeSelect } from './components/ModeSelect';
import { ParentSettings } from './components/ParentSettings';
import { ResultCard } from './components/ResultCard';
import { TrendDashboard } from './components/TrendDashboard';
import { VoiceCheckin } from './components/VoiceCheckin';
import type { CheckinResult, ProfileOut } from './types';

type Screen = 'home' | 'form' | 'voice' | 'result' | 'crisis' | 'dashboard' | 'settings';

export function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [profileLoaded, setProfileLoaded] = useState(false);

  useEffect(() => {
    api
      .getProfile()
      .then(setProfile)
      .catch(() => setProfile(null))
      .finally(() => {
        setProfileLoaded(true);
      });
  }, []);

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

      <main id="main" className={styles.main}>
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
