import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { TextPlugin } from "gsap/TextPlugin";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import Home from "./pages/Home";
import { LanguageProvider } from "./contexts/LanguageContext";

gsap.registerPlugin(TextPlugin, ScrollTrigger);

const router = createBrowserRouter([
    {
        path: "/",
        element: <Home />,
    },
]);

function App() {
    return (
        <LanguageProvider>
            <div className="min-h-screen transition-colors duration-200 dark:bg-gray-900 dark:text-white">
                <RouterProvider router={router} />
            </div>
        </LanguageProvider>
    );
}

export default App;
