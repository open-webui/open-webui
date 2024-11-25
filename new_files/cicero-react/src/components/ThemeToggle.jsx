import { FiSun, FiMoon } from 'react-icons/fi';

const ThemeToggle = ({ isDark, toggleTheme }) => {
  return (
    <button
      onClick={toggleTheme}
      className="fixed top-4 right-4 p-2 rounded-full bg-opacity-20 backdrop-blur-lg
                dark:bg-white dark:bg-opacity-10 bg-black hover:bg-opacity-30
                transition-all duration-200 z-50"
      aria-label="Toggle theme"
    >
      {isDark ? (
        <FiSun className="w-6 h-6 text-[#FF3D00]" />
      ) : (
        <FiMoon className="w-6 h-6 text-black dark:text-white" />
      )}
    </button>
  );
};

export default ThemeToggle;
