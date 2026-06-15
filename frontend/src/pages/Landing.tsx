import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Shield, CheckCircle, Zap, Lock, FileCheck, Users, ArrowRight } from "lucide-react";
import heroImage from "@/assets/hero-image.jpg";

const Landing = () => {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative pt-20 pb-16 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-hero opacity-5"></div>
        <div className="container mx-auto px-4">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <h1 className="text-4xl lg:text-6xl font-bold leading-tight">
                  Protect Your
                  <span className="bg-gradient-hero bg-clip-text text-transparent block">
                    Original Content
                  </span>
                  with Blockchain + AI
                </h1>
                <p className="text-xl text-muted-foreground leading-relaxed">
                  Prove authenticity, detect tampering, and establish ownership with our 
                  revolutionary multi-layer content protection system powered by blockchain 
                  and AI forensics.
                </p>
              </div>
              
              <div className="flex flex-col sm:flex-row gap-4">
                <Button variant="hero" size="xl" asChild>
                  <Link to="/register">
                    Register Content
                    <ArrowRight className="ml-2" />
                  </Link>
                </Button>
                <Button variant="outline" size="xl" asChild>
                  <Link to="/verify">Verify Content</Link>
                </Button>
              </div>

              <div className="flex items-center gap-8 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Shield className="text-success" />
                  Blockchain Secured
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle className="text-success" />
                  AI Powered Detection
                </div>
              </div>
            </div>

            <div className="relative">
              <div className="absolute inset-0 bg-gradient-accent opacity-20 blur-3xl"></div>
              <img 
                src={heroImage} 
                alt="Blockchain content protection visualization"
                className="relative rounded-2xl shadow-elegant w-full"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold mb-4">
              Three-Layer Protection Pipeline
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Our advanced system combines multiple detection methods to ensure 
              comprehensive content authenticity verification.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card className="bg-gradient-card border-0 shadow-elegant hover:shadow-xl transition-smooth">
              <CardContent className="p-8 text-center">
                <div className="bg-primary/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mx-auto mb-6">
                  <Zap className="text-primary text-2xl" />
                </div>
                <h3 className="text-xl font-bold mb-3">SHA-256 Hash</h3>
                <p className="text-muted-foreground">
                  Instant exact match detection for pixel-perfect content identification 
                  and duplicate detection.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-card border-0 shadow-elegant hover:shadow-xl transition-smooth">
              <CardContent className="p-8 text-center">
                <div className="bg-accent/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mx-auto mb-6">
                  <FileCheck className="text-accent text-2xl" />
                </div>
                <h3 className="text-xl font-bold mb-3">Perceptual Hash</h3>
                <p className="text-muted-foreground">
                  Detects near-duplicates and slight modifications using advanced 
                  perceptual fingerprinting technology.
                </p>
              </CardContent>
            </Card>

            <Card className="bg-gradient-card border-0 shadow-elegant hover:shadow-xl transition-smooth">
              <CardContent className="p-8 text-center">
                <div className="bg-success/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mx-auto mb-6">
                  <Lock className="text-success text-2xl" />
                </div>
                <h3 className="text-xl font-bold mb-3">AI Forensics</h3>
                <p className="text-muted-foreground">
                  Advanced AI models detect GAN edits, deepfakes, inpainting, 
                  and other sophisticated tampering attempts.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Use Cases Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold mb-4">
              Trusted by Creators Worldwide
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              From artists to researchers, Authx empowers professionals to protect 
              their original work and establish digital ownership.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { title: "Digital Artists", desc: "Protect artwork from AI theft and unauthorized modifications" },
              { title: "Photographers", desc: "Prove authenticity of images in the age of deepfakes" },
              { title: "Researchers", desc: "Establish priority for scientific discoveries and publications" },
              { title: "Legal Investigators", desc: "Verify evidence integrity in digital forensics cases" }
            ].map((useCase, index) => (
              <Card key={index} className="bg-card border hover:shadow-accent hover:scale-[1.02] transition-bouncy cursor-pointer">
                <CardContent className="p-6">
                  <div className="bg-primary/5 rounded-lg p-3 w-12 h-12 flex items-center justify-center mb-4">
                    <Users className="text-primary" />
                  </div>
                  <h3 className="font-bold mb-2">{useCase.title}</h3>
                  <p className="text-sm text-muted-foreground">{useCase.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-hero text-primary-foreground relative overflow-hidden">
        <div className="absolute inset-0 bg-primary/10"></div>
        <div className="container mx-auto px-4 text-center relative">
          <h2 className="text-3xl lg:text-4xl font-bold mb-6">
            Ready to Protect Your Content?
          </h2>
          <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
            Join thousands of creators who trust Authx to secure their digital assets 
            and prove authenticity with blockchain-backed certificates.
          </p>
          <Button variant="secondary" size="xl" asChild>
            <Link to="/register">
              Get Started Now
              <ArrowRight className="ml-2" />
            </Link>
          </Button>
        </div>
      </section>
    </div>
  );
};

export default Landing;