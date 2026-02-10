import { Link } from 'react-router-dom';
import { Bot, Terminal, Shield, Cpu, ChevronRight } from 'lucide-react';

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-[#0f172a] text-white font-sans overflow-hidden relative">
      {/* Background Gradients */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-blue-900/20 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-indigo-900/20 rounded-full blur-[120px]" />
      </div>

      {/* Navbar */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="bg-gradient-to-tr from-blue-500 to-cyan-400 p-2 rounded-lg">
            <Bot size={24} className="text-white" />
          </div>
          <span className="text-xl font-bold tracking-tight">InfraLens</span>
        </div>

        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-300">
          <a href="#" className="hover:text-white transition-colors">Home</a>
          <Link to="/sign-in" className="hover:text-white transition-colors">
            AI Assistant
          </Link>
          <a href="#" className="hover:text-white transition-colors">Pricing</a>
        </div>

        <div className="flex items-center gap-4">
          <Link to="/sign-in" className="text-sm font-medium text-gray-300 hover:text-white transition-colors">
            Log in
          </Link>
          <Link 
            to="/sign-up" 
            className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-full text-sm font-medium transition-all shadow-lg shadow-blue-900/20"
          >
            Create Account
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex flex-col items-center justify-center text-center mt-20 px-4">
        
        {/* Floating Icons (Decorative) */}
        <div className="absolute top-10 left-[15%] animate-bounce duration-[3000ms]">
          <div className="bg-gray-800/50 p-3 rounded-2xl backdrop-blur-sm border border-gray-700/50">
            <Terminal className="text-blue-400" size={24} />
          </div>
        </div>
        <div className="absolute top-40 right-[15%] animate-bounce duration-[4000ms]">
           <div className="bg-gray-800/50 p-3 rounded-2xl backdrop-blur-sm border border-gray-700/50">
            <Shield className="text-green-400" size={24} />
          </div>
        </div>
        <div className="absolute bottom-[-100px] left-[20%] animate-pulse">
           <div className="bg-gray-800/50 p-3 rounded-2xl backdrop-blur-sm border border-gray-700/50">
            <Cpu className="text-purple-400" size={24} />
          </div>
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 max-w-4xl bg-clip-text text-transparent bg-gradient-to-b from-white to-gray-400">
          Understand Any Codebase <br />
          <span className="text-white">In Minutes, Not Days</span>
        </h1>

        <p className="text-lg md:text-xl text-gray-400 max-w-4xl mb-10 leading-relaxed">
          Clone any GitHub repository and chat with public or your private repository's code using AI.<br />
          Get instant answers about architecture, functions and implementation details.
        </p>


        <div className="flex flex-col md:flex-row items-center gap-4 w-full max-w-md">
          <div className="relative w-full">
            <input 
              type="email" 
              placeholder="Enter your business email" 
              className="w-full bg-gray-900/50 border border-gray-700 text-white px-6 py-4 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all placeholder-gray-500"
            />
          </div>
          <Link 
            to="/sign-up"
            className="w-full md:w-auto whitespace-nowrap bg-amber-500 hover:bg-amber-600 text-black font-bold px-8 py-4 rounded-full transition-all flex items-center justify-center gap-2"
          >
            Signup Free
          </Link>
        </div>

        <div className="mt-12 flex items-center gap-8 text-sm text-gray-500 font-medium">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            Free 14-day trial
          </div>
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            No credit card required
          </div>
        </div>

      </main>
    </div>
  );
};

export default LandingPage;
