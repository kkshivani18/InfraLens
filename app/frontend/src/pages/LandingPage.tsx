import { Link } from 'react-router-dom';
import { Bot, Terminal, Shield, Cpu, ChevronRight, Zap, Search, MessageSquare, Code2 } from 'lucide-react';

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 font-sans selection:bg-blue-500/30">

      {/* Dynamic Background */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-600/10 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600/10 rounded-full blur-[120px] animate-pulse delay-700" />
        <div className="absolute top-[20%] right-[10%] w-[30%] h-[30%] bg-purple-600/5 rounded-full blur-[100px]" />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-100 contrast-150 pointer-events-none"></div>
      </div>

      {/* Navbar */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
        <nav className="max-w-7xl mx-auto flex items-center justify-between px-6 py-3 bg-slate-900/40 backdrop-blur-xl border border-slate-800/50 rounded-2xl shadow-2xl shadow-black/50">
          <div className="flex items-center gap-3 group cursor-pointer">
            <div className="bg-linear-to-tr from-blue-600 to-indigo-500 p-2 rounded-xl shadow-lg shadow-blue-500/20 group-hover:scale-110 transition-transform duration-300">
              <Bot size={22} className="text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              InfraLens
            </span>
          </div>

          <div className="hidden md:flex items-center gap-10 text-sm font-medium">
            <a href="#" className="text-slate-400 hover:text-white transition-colors">Home</a>
            <Link to="/sign-in" className="text-slate-400 hover:text-white transition-colors">AI Assistant</Link>
            <a href="#" className="text-slate-400 hover:text-white transition-colors">Pricing</a>
          </div>

          <div className="flex items-center gap-4">
            <Link to="/sign-in" className="hidden sm:block text-sm font-medium text-slate-400 hover:text-white transition-colors px-4">
              Log in
            </Link>
            <Link 
              to="/sign-up" 
              className="bg-white hover:bg-slate-200 text-slate-950 px-6 py-2.5 rounded-xl text-sm font-bold transition-all hover:shadow-[0_0_20px_rgba(255,255,255,0.3)] active:scale-95"
            >
              Get Started
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 pt-44 pb-20 px-4 flex flex-col items-center">

        {/* Floating Icons */}
        
        <div className="absolute top-35 left-[8%] animate-float hidden lg:block pointer-events-none">
          <div className="bg-slate-900/40 p-4 rounded-2xl backdrop-blur-xl border border-slate-800/50 shadow-2xl shadow-blue-500/10">
            <Terminal className="text-blue-400" size={28} />
          </div>
        </div>
        
        <div className="absolute top-50 right-[15%] animate-float-delayed hidden lg:block pointer-events-none">
          <div className="bg-slate-900/40 p-4 rounded-2xl backdrop-blur-xl border border-slate-800/50 shadow-2xl shadow-indigo-500/10">
            <Shield className="text-indigo-400" size={28} />
          </div>
        </div>
        
        <div className="absolute bottom-170 left-[15%] animate-float-delayed hidden lg:block pointer-events-none">
          <div className="bg-slate-900/40 p-4 rounded-2xl backdrop-blur-xl border border-slate-800/50 shadow-2xl shadow-purple-500/10">
            <Cpu className="text-purple-400" size={28} />
          </div>
        </div>
        
        <div className="absolute bottom-160 right-[5%] animate-float hidden lg:block pointer-events-none">
          <div className="bg-slate-900/40 p-4 rounded-2xl backdrop-blur-xl border border-slate-800/50 shadow-2xl shadow-emerald-500/10">
            <Code2 className="text-emerald-400" size={28} />
          </div>
        </div>

        <h1 className="text-6xl md:text-8xl font-black tracking-tight text-center mb-8 max-w-5xl leading-[1.1]">
          <span className="inline-block bg-clip-text text-transparent bg-gradient-to-b from-white via-white to-slate-500">
            Understand Any Codebase
          </span>
          <br />
          <span className="text-blue-500 relative">
            In Minutes.
            <svg className="absolute -bottom-4 left-0 w-full h-4 text-blue-500/30" viewBox="0 0 100 10" preserveAspectRatio="none">
              {/* <path d="M0 5 Q 25 0 50 5 T 100 5" fill="none" stroke="currentColor" strokeWidth="2" /> */}
            </svg>
          </span>
        </h1>

        <p className="text-xl md:text-2xl text-slate-400 text-center max-w-3xl mb-12 leading-relaxed font-medium">
          InfraLens transforms how you interact with code. Clone any GitHub repo and chat with it to uncover architectural secrets instantly.
        </p>

        <div className="flex flex-col items-center gap-6 w-full max-w-2xl animate-fade-in-up">
          <div className="relative group w-full sm:w-[500px]">
            <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
            <div className="relative flex items-center bg-slate-900 rounded-2xl border border-slate-800 p-1.5 backdrop-blur-xl">
              <input 
                type="email" 
                placeholder="Enter your email to start..." 
                className="flex-1 bg-transparent border-none text-white px-6 py-3 focus:outline-none placeholder-slate-500 font-medium"
              />
              <Link 
                to="/sign-up"
                className="bg-blue-600 hover:bg-blue-500 text-white font-bold px-8 py-3 rounded-xl transition-all flex items-center gap-2 group/btn shadow-lg shadow-blue-600/20"
              >
                Join Beta
                <ChevronRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </Link>
            </div>
          </div>

          <div className="flex flex-wrap justify-center items-center gap-8 text-xs font-bold text-slate-500 uppercase tracking-widest">
            <span className="flex items-center gap-2"><Shield size={14} className="text-emerald-500" /> Enterprise Secure</span>
            <span className="flex items-center gap-2"><Zap size={14} className="text-amber-500" /> Real-time Ingestion</span>
            <span className="flex items-center gap-2"><Code2 size={14} className="text-blue-500" /> Multi-Repo Support</span>
          </div>
        </div>

        {/* Feature Grid */}
        <section className="mt-40 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-7xl w-full px-6">
          
          <FeatureCard 
            icon={<Search className="text-blue-400" />}
            title="Semantic Search"
            description="Find exactly what you're looking for using natural language queries across your entire codebase."
          />
          
          <FeatureCard 
            icon={<MessageSquare className="text-indigo-400" />}
            title="Interactive Chat"
            description="Ask questions about complex functions, dependencies, or architectural patterns and get instant answers."
          />
          
          <FeatureCard 
            icon={<Terminal className="text-purple-400" />}
            title="Repo Analytics"
            description="Visualize your infrastructure and codebase structure with AI-driven insights and summaries."
          />
        
        </section>

        {/* Floating Decorative Elements */}
        
        <div className="fixed top-1/4 -left-12 opacity-20 blur-sm animate-float hidden lg:block">
           <div className="bg-slate-800 p-4 rounded-3xl border border-slate-700 shadow-2xl">
              <div className="w-40 h-2 bg-slate-700 rounded-full mb-3"></div>
              <div className="w-24 h-2 bg-slate-700 rounded-full mb-3"></div>
              <div className="w-32 h-2 bg-slate-700 rounded-full"></div>
           </div>
        </div>
        
        <div className="fixed bottom-1/4 -right-12 opacity-20 blur-sm animate-float-delayed hidden lg:block">
           <div className="bg-slate-800 p-6 rounded-3xl border border-slate-700 shadow-2xl">
              <div className="flex gap-2 mb-4">
                <div className="w-3 h-3 rounded-full bg-red-500/50"></div>
                <div className="w-3 h-3 rounded-full bg-amber-500/50"></div>
                <div className="w-3 h-3 rounded-full bg-emerald-500/50"></div>
              </div>
              <div className="w-48 h-2 bg-slate-700 rounded-full mb-3"></div>
              <div className="w-40 h-2 bg-slate-700 rounded-full"></div>
           </div>
        </div>
      
      </main>

      <footer className="relative z-10 border-t border-slate-900 py-12 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-2 grayscale opacity-50">
            <Bot size={20} />
            <span className="font-bold">InfraLens</span>
          </div>
          <p className="text-slate-500 text-sm">© 2026 InfraLens. Built for developers by developer.</p>
          <div className="flex gap-6 text-slate-500 text-sm">
            <a href="https://github.com/kkshivani18/InfraLens" className="hover:text-white transition-colors">GitHub</a>
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

const FeatureCard = ({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) => (
  <div className="group relative p-8 rounded-3xl bg-slate-900/50 border border-slate-800/50 backdrop-blur-sm hover:bg-slate-800/50 transition-all duration-500 hover:-translate-y-2">
    <div className="absolute -inset-px bg-gradient-to-b from-blue-500/10 to-transparent rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity"></div>
    <div className="relative">
      <div className="bg-slate-950 p-3 rounded-2xl w-fit mb-6 border border-slate-800 shadow-inner group-hover:scale-110 transition-transform duration-500">
        {icon}
      </div>
      <h3 className="text-xl font-bold text-white mb-3 tracking-tight">{title}</h3>
      <p className="text-slate-400 leading-relaxed text-sm font-medium">{description}</p>
    </div>
  </div>
);

export default LandingPage;
