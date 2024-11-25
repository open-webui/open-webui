import { useEffect, useState } from 'react';
import { LightThemeDots, DarkThemeDots } from './';

const DotsBackground = () => {
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  useEffect(() => {
    // Check if the root element has dark theme class
    const checkTheme = () => {
      const isDark = document.documentElement.classList.contains('dark');
      setIsDarkTheme(isDark);
    };

    // Initial check
    checkTheme();

    // Create observer to watch for theme changes
    const observer = new MutationObserver(checkTheme);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });

    return () => observer.disconnect();
  }, []);

  return isDarkTheme ? <DarkThemeDots /> : <LightThemeDots />;
};

export default DotsBackground;

// Usage example:
/*
import { DotsBackground } from './components/animations';

function App() {
  return (
    <div>
      <DotsBackground />
      {/* Your other components *//*}
    </div>
  );
}
*/
