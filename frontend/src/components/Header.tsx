import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Shield, Menu } from "lucide-react";

const Header = () => {
  return (
    <header className="fixed top-0 w-full bg-background/95 backdrop-blur-md border-b z-50">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-2xl font-bold">
            <Shield className="text-primary" />
            <span className="bg-gradient-primary bg-clip-text text-transparent">
              Authx
            </span>
          </Link>
          
          <nav className="hidden md:flex items-center gap-6 ml-40">
            <Link to="/" className="text-foreground hover:text-primary transition-smooth">
              Home
            </Link>
            <Link to="/register" className="text-foreground hover:text-primary transition-smooth">
              Register Content
            </Link>
            <Link to="/about" className="text-foreground hover:text-primary transition-smooth">
              How It Works
            </Link>
          </nav>

          <div className="hidden md:flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link to="/verify">Verify Content</Link>
            </Button>
            <Button variant="hero" asChild>
              <Link to="/register">Get Started</Link>
            </Button>
          </div>

          <Button variant="ghost" size="icon" className="md:hidden">
            <Menu />
          </Button>
        </div>
      </div>
    </header>
  );
};

export default Header;


