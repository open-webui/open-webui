import FaQSection from "../components/fAqSection/FaQSection";
import Footer from "../components/footer/Footer";
import Hero from "../components/HeroSection/Hero";
import Navbar from "../components/navabar/Navbar";
import NewsLetter from "../components/newsLetter/NewsLetter";
import WorkSection from "../components/workSection/WorkSection";

const Home = () => {
    return (
        <div className="bg-[var(--background)] transition-colors duration-300">
            <div className="w-full mx-auto h-screen pb-14 relative overflow-hidden">
                <Navbar />
                <Hero />
            </div>

            <WorkSection />
            <FaQSection />
            <NewsLetter />
            <Footer />
        </div>
    );
};

export default Home;
