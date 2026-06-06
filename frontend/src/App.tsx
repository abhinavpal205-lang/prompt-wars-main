import { useState } from 'react';
import styles from './App.module.css';
import { CrisisScreen } from './components/CrisisScreen';
import { Disclaimer } from './components/Disclaimer';
import { FormCheckin } from './components/FormCheckin';
import { ModeSelect } from './components/ModeSelect';
import { ResultCard } from './components/ResultCard';
import type { CheckinResult } from './types';

type Screen = 'home' | 'form' | 'voice' | 'result' | 'crisis';

export function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [result, setResult] = useState<CheckinResult | null>(null);

  const handleResult = (checkin: CheckinResult) => {
    setResult(checkin);
    // The crisis path overrides everything, before any scoring UI.
    setScreen(checkin.crisis ? 'crisis' : 'result');
  };

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
          <p role="status">Voice check-in is coming right up — try the quick form meanwhile.</p>
        )}
        {screen === 'result' && result && (
          <ResultCard
            result={result}
            onDone={() => {
              setScreen('home');
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
      </main>

      <footer className={styles.footer}>
        <Disclaimer variant="footer" />
      </footer>
    </div>
  );
}
