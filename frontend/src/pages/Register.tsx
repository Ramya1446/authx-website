import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Upload, FileCheck, Shield, Download, CheckCircle, Image as ImageIcon, Music, Video, FileText } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import QRCode from "react-qr-code";
import jsPDF from "jspdf";

const Register = () => {
  const [step, setStep] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [formData, setFormData] = useState({
    creatorName: "",
    contentType: "",
    description: "",
    aiTool: ""
  });
  const [proofData, setProofData] = useState<any>(null);
  const [tamperAnalysis, setTamperAnalysis] = useState<any>(null);
  const { toast } = useToast();

  const getContentTypeIcon = (type: string) => {
    if (type.startsWith("image")) return <ImageIcon className="text-blue-500" />;
    if (type.startsWith("audio")) return <Music className="text-purple-500" />;
    if (type.startsWith("video")) return <Video className="text-red-500" />;
    return <FileText className="text-green-500" />;
  };

  const getContentTypeLabel = (type: string) => {
    if (type.startsWith("image")) return "Image";
    if (type.startsWith("audio")) return "Audio";
    if (type.startsWith("video")) return "Video";
    if (type.includes("pdf")) return "PDF";
    return "Document";
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      
      // Auto-detect content type
      const fileType = selectedFile.type;
      let detectedType = "";
      
      if (fileType.startsWith("image")) detectedType = "image";
      else if (fileType.startsWith("audio")) detectedType = "audio";
      else if (fileType.startsWith("video")) detectedType = "video";
      else if (fileType.includes("pdf")) detectedType = "text";
      else detectedType = "text";
      
      setFormData({ ...formData, contentType: detectedType });
      
      toast({
        title: "File uploaded successfully",
        description: `${selectedFile.name} (${getContentTypeLabel(fileType)}) is ready for registration.`,
      });
    }
  };

  const handleRegister = async () => {
    if (!file || !formData.creatorName || !formData.contentType) {
      toast({
        title: "Missing information",
        description: "Please fill in all required fields and upload a file.",
        variant: "destructive"
      });
      return;
    }

    setIsProcessing(true);
    setStep(2);

    const form = new FormData();
    form.append("owner_name", formData.creatorName);
    form.append("owner_address", formData.aiTool || "");
    form.append("content_type", formData.contentType);
    form.append("description", formData.description || "");
    form.append("ai_tool", formData.aiTool || "");
    form.append("file", file);

    try {
      const res = await fetch("http://127.0.0.1:8000/register", {
        method: "POST",
        body: form
      });
      const data = await res.json();
      
      if (data.status === "ok") {
        setProofData(data.proof);
        setTamperAnalysis(data.proof.tampering_analysis);
        toast({
          title: "Registration complete!",
          description: "Your content has been successfully registered on the blockchain.",
        });
        setStep(3);
      } else if (data.status === "already_registered") {
        toast({
          title: "⛔ Content Already Registered",
          description: `This exact content was registered by ${data.existing_record.owner}`,
          variant: "destructive"
        });
        setStep(1);
        setIsProcessing(false);
        return;
      } else if (data.status === "similar_content_exists") {
        // Enhanced error display for similar content
        const contentTypeName = data.content_type || getContentTypeLabel(file.type);
        const aiFlag = data.ai_tampering_detected ? "🤖 AI-Modified " : "";
        
        toast({
          title: `⚠️ ${aiFlag}Similar ${contentTypeName} Detected`,
          description: `${data.similarity} similar to content by ${data.original_record.owner_name}. ${data.recommendation}`,
          variant: "destructive"
        });
        
        // Show detailed alert with all distances
        if (data.all_distances) {
          console.log("Similarity Details:", data.all_distances);
          console.log("Best Match Algorithm:", data.best_match_algorithm);
          console.log("Tampering Score:", data.tampering_score);
        }
        
        setStep(1);
        setIsProcessing(false);
        return;
      } else if (data.status === "high_tampering_detected") {
        toast({
          title: "🔍 High AI Tampering Detected",
          description: data.message + " - " + data.recommendation,
          variant: "destructive"
        });
        setStep(1);
        setIsProcessing(false);
        return;
      } else {
        toast({
          title: "Registration failed",
          description: data.message || data.status,
          variant: "destructive"
        });
        setStep(1);
        setIsProcessing(false);
        return;
      }
    } catch (err) {
      toast({
        title: "Error",
        description: "Unable to reach backend. Please ensure the server is running.",
        variant: "destructive"
      });
      setStep(1);
      setIsProcessing(false);
      return;
    }

    setIsProcessing(false);
  };

  const generatePDF = () => {
    if (!proofData) return;
    const doc = new jsPDF();
    
    doc.setFontSize(20);
    doc.text("Authx Ownership Certificate", 20, 20);
    
    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    doc.text("Multi-Content Protection with AI Verification", 20, 28);
    
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(12);
    
    doc.text(`Content ID: ${proofData.id}`, 20, 45);
    doc.text(`Creator: ${formData.creatorName}`, 20, 55);
    doc.text(`Content Type: ${formData.contentType.toUpperCase()}`, 20, 65);
    doc.text(`SHA-256: ${proofData.sha256}`, 20, 75, { maxWidth: 170 });
    
    let yPos = 85;
    
    // Add fingerprints based on content type
    if (proofData.phash) {
      doc.text(`Perceptual Hash: ${proofData.phash}`, 20, yPos);
      yPos += 10;
    }
    
    if (proofData.fingerprints) {
      Object.entries(proofData.fingerprints).forEach(([key, value]) => {
        if (value && key !== 'phash') {
          const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
          doc.text(`${label}: ${String(value).substring(0, 40)}...`, 20, yPos);
          yPos += 10;
        }
      });
    }
    
    if (proofData.tx_hash) {
      doc.text(`Transaction Hash: ${proofData.tx_hash}`, 20, yPos);
      yPos += 10;
    }
    
    if (proofData.block_number) {
      doc.text(`Block Number: ${proofData.block_number}`, 20, yPos);
      yPos += 10;
    }
    
    yPos += 5;
    
    // AI Analysis Results
    if (tamperAnalysis) {
      doc.setFontSize(14);
      doc.text("AI Authenticity Analysis", 20, yPos);
      yPos += 10;
      
      doc.setFontSize(11);
      const tamperScore = (tamperAnalysis.tamper_probability * 100).toFixed(1);
      const tamperStatus = getTamperStatusText(tamperAnalysis.tamper_probability);
      
      doc.text(`Tamper Score: ${tamperScore}%`, 20, yPos);
      yPos += 8;
      doc.text(`Status: ${tamperStatus}`, 20, yPos);
      yPos += 8;
      doc.text(`Confidence: ${(tamperAnalysis.confidence * 100).toFixed(1)}%`, 20, yPos);
      yPos += 8;
      
      if (tamperAnalysis.detected_artifacts && tamperAnalysis.detected_artifacts.length > 0) {
        doc.text(`Detected Artifacts:`, 20, yPos);
        yPos += 8;
        doc.setFontSize(10);
        doc.text(tamperAnalysis.detected_artifacts.join(', '), 25, yPos, { maxWidth: 160 });
        yPos += 10;
      }
    }
    
    yPos += 5;
    doc.setFontSize(12);
    doc.text(`Registration Date: ${new Date().toLocaleString()}`, 20, yPos);
    yPos += 10;
    doc.text(`Verification URL: ${proofData.proof_url}`, 20, yPos);
    
    // Add footer
    doc.setFontSize(8);
    doc.setTextColor(150, 150, 150);
    doc.text("This certificate is cryptographically secured and verifiable on the blockchain.", 20, 280);
    
    doc.save(`Authx_Certificate_${formData.contentType}_${proofData.id}.pdf`);
  };

  const resetForm = () => {
    setStep(1);
    setFile(null);
    setFormData({ creatorName: "", contentType: "", description: "", aiTool: "" });
    setProofData(null);
    setTamperAnalysis(null);
  };

  const getTamperStatusText = (score: number) => {
    if (score < 0.3) return "Low Risk - Likely Original";
    if (score < 0.6) return "Medium Risk - Some Modifications Detected";
    return "High Risk - Significant AI Tampering Detected";
  };

  const getTamperColor = (score: number) => {
    if (score < 0.3) return "text-green-600";
    if (score < 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="min-h-screen pt-20 pb-16">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Register Your Content</h1>
          <p className="text-xl text-muted-foreground">
            Secure images, videos, audio, and documents with blockchain-backed proof and AI authenticity verification
          </p>
        </div>

        {step === 1 && (
          <Card className="bg-gradient-card shadow-elegant">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="text-primary" />
                Upload and Register Content
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* File Upload */}
              <div className="space-y-2">
                <Label htmlFor="file">Content File *</Label>
                <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center hover:border-primary/50 transition-smooth">
                  <input
                    id="file"
                    type="file"
                    onChange={handleFileUpload}
                    className="hidden"
                    accept="image/*,audio/*,video/*,.txt,.pdf,.doc,.docx"
                  />
                  <label htmlFor="file" className="cursor-pointer">
                    {file ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-center gap-2">
                          {getContentTypeIcon(file.type)}
                          <FileCheck className="text-success text-3xl" />
                        </div>
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {(file.size / 1024 / 1024).toFixed(2)} MB • {getContentTypeLabel(file.type)}
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <div className="flex justify-center gap-4">
                          <ImageIcon className="text-blue-500 text-2xl" />
                          <Music className="text-purple-500 text-2xl" />
                          <Video className="text-red-500 text-2xl" />
                          <FileText className="text-green-500 text-2xl" />
                        </div>
                        <Upload className="text-muted-foreground mx-auto text-3xl" />
                        <p className="font-medium">Click to upload or drag and drop</p>
                        <p className="text-sm text-muted-foreground">
                          Images • Videos • Audio • PDFs • Documents
                        </p>
                        <p className="text-xs text-primary">
                          ✨ AI Detection Enabled for All Content Types
                        </p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Creator Info */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="creator">Creator Name *</Label>
                  <Input
                    id="creator"
                    value={formData.creatorName}
                    onChange={(e) => setFormData({ ...formData, creatorName: e.target.value })}
                    placeholder="Your name or organization"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="type">Content Type *</Label>
                  <Select value={formData.contentType} onValueChange={(value) => setFormData({ ...formData, contentType: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Auto-detected or select manually" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="image">🖼️ Image/Artwork</SelectItem>
                      <SelectItem value="audio">🎵 Audio/Music</SelectItem>
                      <SelectItem value="video">🎬 Video</SelectItem>
                      <SelectItem value="text">📄 Document/PDF</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of your content and its significance..."
                  rows={3}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ai-tool">AI Tool Used (if any)</Label>
                <Input
                  id="ai-tool"
                  value={formData.aiTool}
                  onChange={(e) => setFormData({ ...formData, aiTool: e.target.value })}
                  placeholder="e.g., Midjourney, Suno, Runway, ChatGPT, None"
                />
                <p className="text-xs text-muted-foreground">
                  💡 Transparency about AI usage helps establish authenticity and builds trust
                </p>
              </div>

              <Button onClick={handleRegister} className="w-full" size="lg" variant="hero">
                <Shield className="mr-2" />
                Register on Blockchain with AI Verification
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card className="bg-gradient-card shadow-elegant">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="text-primary animate-pulse" />
                Processing Registration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-16 w-16 border-4 border-primary border-t-transparent mx-auto mb-4"></div>
                <p className="text-lg font-medium">Analyzing and securing your content...</p>
                <p className="text-muted-foreground">Running multi-format AI detection and blockchain registration</p>
              </div>
              <div className="space-y-2 text-center text-sm text-muted-foreground">
                <p>✓ Computing cryptographic hashes (SHA-256)</p>
                <p>✓ Generating content fingerprints ({formData.contentType})</p>
                <p>✓ Performing AI authenticity analysis</p>
                <p>✓ Checking for similar registered content</p>
                <p>✓ Recording immutable proof on blockchain</p>
              </div>
              <Progress value={85} className="w-full" />
            </CardContent>
          </Card>
        )}

        {step === 3 && proofData && (
          <Card className="bg-gradient-card shadow-success border-success/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="text-success" />
                Registration Complete!
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center py-6">
                <div className="bg-success/10 rounded-full p-6 w-24 h-24 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="text-success text-4xl" />
                </div>
                <h3 className="text-2xl font-bold mb-2">
                  {formData.contentType.charAt(0).toUpperCase() + formData.contentType.slice(1)} Successfully Registered
                </h3>
                <p className="text-muted-foreground mb-4">
                  Your content is now secured with blockchain and AI verification.
                </p>
                
                <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                  <div>
                    <p className="font-mono text-primary">ID: {proofData.id}</p>
                  </div>
                  <div>
                    {proofData.tamper_score !== undefined && (
                      <p className={`font-medium ${getTamperColor(proofData.tamper_score)}`}>
                        Tamper Score: {(proofData.tamper_score * 100).toFixed(1)}%
                      </p>
                    )}
                  </div>
                </div>
                
                {proofData.tx_hash && (
                  <p className="text-xs font-mono mb-2 break-all">
                    Blockchain TX: {proofData.tx_hash}
                  </p>
                )}
                
                {proofData.block_number && (
                  <p className="text-xs font-mono mb-4">
                    Block: {proofData.block_number}
                  </p>
                )}
              </div>

              {/* AI Analysis Results */}
              {tamperAnalysis && (
                <div className="bg-muted/30 rounded-lg p-4 mb-4">
                  <h4 className="font-semibold mb-2 flex items-center gap-2">
                    🤖 AI Authenticity Analysis
                  </h4>
                  <div className="space-y-2 text-sm">
                    <p className={`font-medium ${getTamperColor(tamperAnalysis.tamper_probability)}`}>
                      Status: {getTamperStatusText(tamperAnalysis.tamper_probability)}
                    </p>
                    <p>Confidence Level: {(tamperAnalysis.confidence * 100).toFixed(1)}%</p>
                    {tamperAnalysis.detected_artifacts && tamperAnalysis.detected_artifacts.length > 0 && (
                      <p>Detected Patterns: {tamperAnalysis.detected_artifacts.join(', ')}</p>
                    )}
                  </div>
                </div>
              )}

              {/* Fingerprint Info */}
              {proofData.fingerprints && Object.keys(proofData.fingerprints).length > 0 && (
                <div className="bg-muted/20 rounded-lg p-4 mb-4">
                  <h4 className="font-semibold mb-2 text-sm">🔐 Content Fingerprints Generated</h4>
                  <div className="space-y-1 text-xs text-muted-foreground">
                    {Object.keys(proofData.fingerprints).map(key => (
                      <p key={key}>✓ {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="bg-muted/30 rounded-lg p-6 space-y-4">
                <h4 className="font-semibold flex items-center gap-2">
                  <FileCheck className="text-primary" />
                  Your Ownership Certificate
                </h4>
                <div className="grid sm:grid-cols-2 gap-3">
                  <Button variant="accent" className="w-full" onClick={generatePDF}>
                    <Download className="mr-2" />
                    Download Certificate
                  </Button>
                  <div className="flex justify-center items-center w-full border rounded-lg p-2">
                    <QRCode value={`http://127.0.0.1:8000/proof/${proofData.id}`} size={100} />
                  </div>
                </div>
                <p className="text-xs text-muted-foreground text-center">
                  Certificate includes AI analysis, fingerprints, and blockchain verification
                </p>
              </div>

              <div className="text-center">
                <Button variant="hero" onClick={resetForm}>
                  Register Another File
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Register;