import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Link } from "react-router-dom";
import { 
  Shield, 
  Zap, 
  FileCheck, 
  Lock, 
  ArrowRight, 
  CheckCircle, 
  AlertTriangle,
  Brain,
  Blocks,
  Hash
} from "lucide-react";

const About = () => {
  return (
    <div className="min-h-screen pt-20 pb-16">
      <div className="container mx-auto px-4 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl lg:text-5xl font-bold mb-6">
            How <span className="bg-gradient-hero bg-clip-text text-transparent">Authx</span> Works
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto">
            Understanding our revolutionary three-layer content authentication pipeline 
            that combines blockchain immutability with AI-powered forensic analysis.
          </p>
        </div>

        {/* Three Layer Pipeline */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold text-center mb-12">Three-Layer Detection Pipeline</h2>
          
          <div className="grid lg:grid-cols-3 gap-8">
            {/* Layer 1: SHA-256 */}
            <Card className="bg-gradient-card shadow-elegant hover:shadow-xl transition-smooth border-l-4 border-l-primary">
              <CardHeader className="text-center">
                <div className="bg-primary/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mx-auto mb-4">
                  <Hash className="text-primary text-2xl" />
                </div>
                <CardTitle className="flex items-center justify-center gap-2">
                  <Badge className="bg-primary text-primary-foreground">Layer 1</Badge>
                </CardTitle>
                <h3 className="text-2xl font-bold">SHA-256 Hash</h3>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-muted-foreground">
                  Cryptographic hashing for exact match detection. Every byte of your content 
                  is converted into a unique 256-bit fingerprint.
                </p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>Instant exact match detection</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>100% accuracy for identical content</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>Cryptographically secure</span>
                  </div>
                </div>
                <div className="bg-muted/30 p-3 rounded-lg">
                  <p className="text-xs font-mono break-all">
                    a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Layer 2: pHash */}
            <Card className="bg-gradient-card shadow-elegant hover:shadow-xl transition-smooth border-l-4 border-l-accent">
              <CardHeader className="text-center">
                <div className="bg-accent/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mx-auto mb-4">
                  <FileCheck className="text-accent text-2xl" />
                </div>
                <CardTitle className="flex items-center justify-center gap-2">
                  <Badge className="bg-accent text-accent-foreground">Layer 2</Badge>
                </CardTitle>
                <h3 className="text-2xl font-bold">Perceptual Hash</h3>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-muted-foreground">
                  Advanced perceptual fingerprinting detects near-duplicates and slight 
                  modifications while ignoring format changes.
                </p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>Detects resized/compressed content</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>Ignores format conversions</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <AlertTriangle className="text-warning w-4 h-4" />
                    <span>Catches minor modifications</span>
                  </div>
                </div>
                <div className="bg-muted/30 p-3 rounded-lg">
                  <p className="text-sm">
                    <span className="font-medium">Similarity Score:</span> 87% Match
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Content appears to be a modified version
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Layer 3: AI Forensics */}
            <Card className="bg-gradient-card shadow-elegant hover:shadow-xl transition-smooth border-l-4 border-l-success">
              <CardHeader className="text-center">
                <div className="bg-success/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mx-auto mb-4">
                  <Brain className="text-success text-2xl" />
                </div>
                <CardTitle className="flex items-center justify-center gap-2">
                  <Badge className="bg-success text-success-foreground">Layer 3</Badge>
                </CardTitle>
                <h3 className="text-2xl font-bold">AI Forensics</h3>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-muted-foreground">
                  State-of-the-art neural networks trained to detect sophisticated 
                  manipulations including deepfakes and GAN-based edits.
                </p>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>Detects GAN artifacts</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>Identifies inpainting/outpainting</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle className="text-success w-4 h-4" />
                    <span>Deepfake detection</span>
                  </div>
                </div>
                <div className="bg-muted/30 p-3 rounded-lg">
                  <p className="text-sm">
                    <span className="font-medium">Analysis:</span> Authentic Content
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    No tampering artifacts detected
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* Blockchain Integration */}
        <section className="mb-20">
          <Card className="bg-gradient-primary text-primary-foreground">
            <CardContent className="p-12">
              <div className="grid lg:grid-cols-2 gap-8 items-center">
                <div>
                  <div className="flex items-center gap-3 mb-6">
                    <Blocks className="text-3xl" />
                    <h2 className="text-3xl font-bold">Blockchain Integration</h2>
                  </div>
                  <p className="text-lg opacity-90 mb-6">
                    Your content fingerprints are permanently stored on an immutable blockchain, 
                    creating tamper-proof ownership records that can't be altered or deleted.
                  </p>
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <Shield className="text-xl" />
                      <span>Immutable ownership records</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <Lock className="text-xl" />
                      <span>Cryptographically secured timestamps</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <CheckCircle className="text-xl" />
                      <span>Verifiable proof of creation</span>
                    </div>
                  </div>
                </div>
                <div className="bg-white/10 rounded-2xl p-6 space-y-4">
                  <h3 className="font-bold text-lg">Sample Blockchain Record</h3>
                  <div className="font-mono text-sm space-y-2 opacity-90">
                    <p><span className="opacity-70">Block:</span> #2,847,392</p>
                    <p><span className="opacity-70">Txn ID:</span> 0x1a2b3c...</p>
                    <p><span className="opacity-70">Creator:</span> artist@domain.com</p>
                    <p><span className="opacity-70">SHA256:</span> a665a459...</p>
                    <p><span className="opacity-70">Timestamp:</span> 2024-01-15 14:30:22 UTC</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Use Cases */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold text-center mb-12">Real-World Applications</h2>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                title: "Digital Artists",
                description: "Protect artwork from AI theft and prove originality in the age of generative AI.",
                icon: "🎨"
              },
              {
                title: "Photographers", 
                description: "Combat deepfakes and establish authentic image provenance for media verification.",
                icon: "📸"
              },
              {
                title: "Researchers",
                description: "Establish publication priority and prevent plagiarism of academic work.",
                icon: "🔬"
              },
              {
                title: "Legal Professionals",
                description: "Verify digital evidence integrity in court proceedings and investigations.",
                icon: "⚖️"
              }
            ].map((useCase, index) => (
              <Card key={index} className="text-center hover:shadow-accent hover:scale-[1.02] transition-bouncy">
                <CardContent className="p-6">
                  <div className="text-4xl mb-4">{useCase.icon}</div>
                  <h3 className="font-bold text-lg mb-2">{useCase.title}</h3>
                  <p className="text-sm text-muted-foreground">{useCase.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* FAQ */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold text-center mb-12">Frequently Asked Questions</h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            {[
              {
                q: "What if my content is AI-generated?",
                a: "You can still register AI-generated content as your own creative work. Simply specify the AI tool used during registration for transparency."
              },
              {
                q: "How strong is this proof in legal cases?",
                a: "Blockchain records provide cryptographic proof of registration time and content integrity, which has been accepted as evidence in various jurisdictions."
              },
              {
                q: "Can I detect AI-generated modifications?",
                a: "Yes, our AI forensics layer is specifically trained to detect GAN artifacts, deepfakes, and other AI-powered manipulations."
              },
              {
                q: "What happens if someone claims my registered content?",
                a: "Your blockchain registration provides immutable proof of priority. The earlier timestamp and matching fingerprints establish your claim."
              }
            ].map((faq, index) => (
              <Card key={index} className="bg-gradient-card">
                <CardContent className="p-6">
                  <h3 className="font-bold mb-2">{faq.q}</h3>
                  <p className="text-muted-foreground text-sm">{faq.a}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* CTA */}
        <div className="text-center">
          <h2 className="text-3xl font-bold mb-6">Ready to Protect Your Content?</h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join thousands of creators who trust Authx to secure their digital assets 
            and establish ownership with blockchain-backed certificates.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button variant="hero" size="xl" asChild>
              <Link to="/register">
                Start Registration
                <ArrowRight className="ml-2" />
              </Link>
            </Button>
            <Button variant="outline" size="xl" asChild>
              <Link to="/verify">Try Verification</Link>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default About;