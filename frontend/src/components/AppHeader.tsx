import styles from './AppHeader.module.css';

interface AppHeaderProps {
  /** Hide Dashboard/Settings during onboarding; crisis help always shows. */
  showNav: boolean;
  onHome: () => void;
  onDashboard: () => void;
  onSettings: () => void;
  onCrisis: () => void;
}

/** Persistent top bar: brand, navigation, and the always-reachable crisis link. */
export function AppHeader({ showNav, onHome, onDashboard, onSettings, onCrisis }: AppHeaderProps) {
  return (
    <header className={styles.header}>
      <button type="button" className={styles.brand} onClick={onHome}>
        Sahaay
      </button>
      <nav aria-label="Main">
        {showNav && (
          <>
            <button type="button" className={styles.navLink} onClick={onDashboard}>
              Dashboard
            </button>
            <button type="button" className={styles.navLink} onClick={onSettings}>
              Settings
            </button>
          </>
        )}
        <button type="button" className={styles.crisisLink} onClick={onCrisis}>
          Need help now?
        </button>
      </nav>
    </header>
  );
}
