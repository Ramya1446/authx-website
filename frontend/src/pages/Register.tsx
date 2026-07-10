import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { Upload, FileCheck, Shield, Download, CheckCircle, Image as ImageIcon, Music, Video, FileText, AlertTriangle, XCircle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import QRCode from "react-qr-code";
import jsPDF from "jspdf";

// ── Types ────────────────────────────────────────────────────
interface BlockedContentState {
  reason: "similar" | "duplicate" | "high_tampering";
  title: string;
  message: string;
  similarity?: string;
  originalOwner?: string;
  tamperingScore?: number;
}

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
  const [blockedState, setBlockedState] = useState<BlockedContentState | null>(null);
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
      const fileType = selectedFile.type;
      let detectedType = "";
      if (fileType.startsWith("image")) detectedType = "image";
      else if (fileType.startsWith("audio")) detectedType = "audio";
      else if (fileType.startsWith("video")) detectedType = "video";
      else if (fileType.includes("pdf")) detectedType = "text";
      else detectedType = "text";
      setFormData({ ...formData, contentType: detectedType });
      toast({
        title: "File selected",
        description: `${selectedFile.name} · ${(selectedFile.size / 1024 / 1024).toFixed(2)} MB`,
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
    setBlockedState(null);
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
        setStep(3);
        toast({ title: "Registered successfully", description: "Your content is now on-chain." });

      } else if (data.status === "already_registered") {
        setBlockedState({
          reason: "duplicate",
          title: "Already registered",
          message: `This exact file is already registered by ${data.existing_record?.owner ?? "another creator"}.`,
        });
        setStep(4);

      } else if (data.status === "similar_content_exists") {
        setBlockedState({
          reason: "similar",
          title: data.ai_tampering_detected
            ? "AI-modified copy detected"
            : "Similar content exists",
          message: data.message,
          similarity: data.similarity,
          originalOwner: data.original_record?.owner_name,
          tamperingScore: data.tampering_score,
        });
        setStep(4);

      } else if (data.status === "high_tampering_detected") {
        setBlockedState({
          reason: "high_tampering",
          title: "Heavy AI modification detected",
          message: data.message,
          tamperingScore: data.tampering_analysis?.tamper_probability,
        });
        setStep(4);

      } else {
        toast({ title: "Registration failed", description: data.message ?? data.status, variant: "destructive" });
        setStep(1);
      }
    } catch {
      toast({ title: "Connection error", description: "Cannot reach backend — is the server running?", variant: "destructive" });
      setStep(1);
    }

    setIsProcessing(false);
  };

  const generatePDF = () => {
    if (!proofData) return;
    const doc = new jsPDF();
    doc.setFontSize(20);
    doc.text("AuthX Ownership Certificate", 20, 20);
    doc.setFontSize(10);
    doc.setTextColor(100, 100, 100);
    doc.text("Hybrid AI-Blockchain Content Authentication", 20, 28);
    doc.setTextColor(0, 0, 0);
    doc.setFontSize(12);
    doc.text(`Content ID: ${proofData.id}`, 20, 45);
    doc.text(`Creator: ${formData.creatorName}`, 20, 55);
    doc.text(`Content Type: ${formData.contentType.toUpperCase()}`, 20, 65);
    doc.text(`SHA-256: ${proofData.sha256}`, 20, 75, { maxWidth: 170 });
    let y = 90;
    if (proofData.tx_hash) { doc.text(`TX Hash: ${proofData.tx_hash}`, 20, y); y += 10; }
    if (proofData.block_number) { doc.text(`Block: ${proofData.block_number}`, 20, y); y += 10; }
    doc.setFontSize(8);
    doc.setTextColor(150, 150, 150);
    doc.text("Cryptographically secured — verifiable on-chain.", 20, 280);
    doc.save(`AuthX_Certificate_${proofData.id}.pdf`);
  };

  const resetForm = () => {
    setStep(1);
    setFile(null);
    setFormData({ creatorName: "", contentType: "", description: "", aiTool: "" });
    setProofData(null);
    setBlockedState(null);
  };

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="min-h-screen pt-20 pb-16">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Register Your Content</h1>
          <p className="text-xl text-muted-foreground">
            Secure images, videos, audio, and documents with blockchain-backed proof and multimodal forensic verification
          </p>
        </div>

        {/* ── Step 1: Upload form ───────────────────────────── */}
        {step === 1 && (
          <Card className="bg-gradient-card shadow-elegant">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="text-primary" />
                Upload and Register Content
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="file">Content File *</Label>
                <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center hover:border-primary/50 transition-smooth">
                  <input id="file" type="file" onChange={handleFileUpload} className="hidden"
                    accept="image/*,audio/*,video/*,.txt,.pdf,.doc,.docx" />
                  <label htmlFor="file" className="cursor-pointer">
                    {file ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-center gap-2">
                          {getContentTypeIcon(file.type)}
                          <FileCheck className="text-success text-3xl" />
                        </div>
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {(file.size / 1024 / 1024).toFixed(2)} MB · {getContentTypeLabel(file.type)}
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
                        <p className="text-sm text-muted-foreground">Images · Videos · Audio · PDFs · Documents</p>
                        <p className="text-xs text-primary">✨ Multimodal forensic analysis on all content types</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="creator">Creator Name *</Label>
                  <Input id="creator" value={formData.creatorName}
                    onChange={(e) => setFormData({ ...formData, creatorName: e.target.value })}
                    placeholder="Your name or organization" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="type">Content Type *</Label>
                  <Select value={formData.contentType} onValueChange={(v) => setFormData({ ...formData, contentType: v })}>
                    <SelectTrigger><SelectValue placeholder="Auto-detected or select manually" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="image">🖼️ Image / Artwork</SelectItem>
                      <SelectItem value="audio">🎵 Audio / Music</SelectItem>
                      <SelectItem value="video">🎬 Video</SelectItem>
                      <SelectItem value="text">📄 Document / PDF</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of your content..." rows={3} />
              </div>

              <div className="space-y-2">
                <Label htmlFor="ai-tool">AI Tool Used (if any)</Label>
                <Input id="ai-tool" value={formData.aiTool}
                  onChange={(e) => setFormData({ ...formData, aiTool: e.target.value })}
                  placeholder="e.g., Midjourney, Suno, Runway, None" />
                <p className="text-xs text-muted-foreground">
                  Transparency about AI usage helps establish authenticity
                </p>
              </div>

              <Button onClick={handleRegister} className="w-full" size="lg" variant="hero">
                <Shield className="mr-2" />
                Register with Blockchain + Forensic Verification
              </Button>
            </CardContent>
          </Card>
        )}

        {/* ── Step 2: Processing ───────────────────────────── */}
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
                <div className="animate-spin rounded-full h-16 w-16 border-4 border-primary border-t-transparent mx-auto mb-4" />
                <p className="text-lg font-medium">Running multimodal forensic analysis…</p>
                <p className="text-muted-foreground">This may take a moment for video files</p>
              </div>
              <div className="space-y-1 text-center text-sm text-muted-foreground">
                <p>✓ Computing SHA-256 and perceptual hashes</p>
                <p>✓ Generating content fingerprint ({formData.contentType})</p>
                <p>✓ Multimodal forensics — tampering localisation</p>
                <p>✓ Similarity check against registered content</p>
                <p>✓ Recording immutable proof on blockchain</p>
              </div>
              <Progress value={85} className="w-full" />
            </CardContent>
          </Card>
        )}

        {/* ── Step 3: Success ──────────────────────────────── */}
        {step === 3 && proofData && (
          <Card className="bg-gradient-card shadow-success border-success/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="text-success" />
                Registration Complete
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center py-4">
                <div className="bg-success/10 rounded-full p-6 w-24 h-24 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle className="text-success text-4xl" />
                </div>
                <h3 className="text-2xl font-bold mb-1">
                  {formData.contentType.charAt(0).toUpperCase() + formData.contentType.slice(1)} Registered
                </h3>
                <p className="text-muted-foreground">Secured with blockchain proof and forensic verification.</p>
              </div>

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-muted/30 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground mb-0.5">Content ID</p>
                  <p className="font-mono font-medium">{proofData.id}</p>
                </div>
                <div className="bg-muted/30 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground mb-0.5">Block</p>
                  <p className="font-mono font-medium">{proofData.block_number ?? "—"}</p>
                </div>
              </div>

              {proofData.tx_hash && (
                <div className="bg-muted/20 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground mb-0.5">Blockchain TX</p>
                  <p className="text-xs font-mono break-all">{proofData.tx_hash}</p>
                </div>
              )}

              <div className="bg-muted/30 rounded-lg p-6 space-y-4">
                <h4 className="font-semibold flex items-center gap-2">
                  <FileCheck className="text-primary" />
                  Ownership Certificate
                </h4>
                <div className="grid sm:grid-cols-2 gap-3">
                  <Button variant="accent" className="w-full" onClick={generatePDF}>
                    <Download className="mr-2" />
                    Download Certificate
                  </Button>
                  <div className="flex justify-center items-center border rounded-lg p-2">
                    <QRCode value={`http://127.0.0.1:8000/proof/${proofData.id}`} size={100} />
                  </div>
                </div>
              </div>

              <div className="text-center">
                <Button variant="hero" onClick={resetForm}>Register Another File</Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── Step 4: Blocked ──────────────────────────────── */}
        {step === 4 && blockedState && (
          <Card className="bg-gradient-card shadow-elegant border-destructive/20">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                {blockedState.reason === "duplicate" ? (
                  <XCircle className="text-destructive" />
                ) : (
                  <AlertTriangle className="text-destructive" />
                )}
                Registration Blocked
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">

              {/* Primary message */}
              <div className="bg-destructive/5 border border-destructive/20 rounded-lg p-4">
                <p className="font-semibold text-destructive mb-1">{blockedState.title}</p>
                <p className="text-sm text-muted-foreground">{blockedState.message}</p>
              </div>

              {/* Similarity details */}
              {blockedState.reason === "similar" && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {blockedState.similarity && (
                    <div className="bg-muted/30 rounded-lg p-3">
                      <p className="text-xs text-muted-foreground mb-0.5">Similarity</p>
                      <p className="text-lg font-bold text-destructive">{blockedState.similarity}</p>
                    </div>
                  )}
                  {blockedState.tamperingScore !== undefined && (
                    <div className="bg-muted/30 rounded-lg p-3">
                      <p className="text-xs text-muted-foreground mb-0.5">AI tampering probability</p>
                      <p className="text-lg font-bold text-orange-600">
                        {(blockedState.tamperingScore * 100).toFixed(1)}%
                      </p>
                    </div>
                  )}
                  {blockedState.originalOwner && (
                    <div className="bg-muted/30 rounded-lg p-3 col-span-2">
                      <p className="text-xs text-muted-foreground mb-0.5">Registered owner</p>
                      <p className="font-medium">{blockedState.originalOwner}</p>
                    </div>
                  )}
                </div>
              )}

              {/* high_tampering details */}
              {blockedState.reason === "high_tampering" && blockedState.tamperingScore !== undefined && (
                <div className="bg-muted/30 rounded-lg p-3 text-sm">
                  <p className="text-xs text-muted-foreground mb-0.5">AI tampering probability</p>
                  <p className="text-lg font-bold text-orange-600">
                    {(blockedState.tamperingScore * 100).toFixed(1)}%
                  </p>
                </div>
              )}

              {/* What this means */}
              <div className="bg-muted/20 rounded-lg p-4 space-y-2">
                <p className="text-sm font-semibold">What this means</p>
                {blockedState.reason === "duplicate" && (
                  <p className="text-sm text-muted-foreground">
                    The exact file (SHA-256 match) is already registered. If you are the original creator,
                    contact support with your proof of creation.
                  </p>
                )}
                {blockedState.reason === "similar" && (
                  <p className="text-sm text-muted-foreground">
                    AuthX detected that this {formData.contentType} is derived from already-registered content —
                    either a trim, crop, re-encode, or AI-assisted modification. Registration is blocked to protect
                    the original creator's rights.
                  </p>
                )}
                {blockedState.reason === "high_tampering" && (
                  <p className="text-sm text-muted-foreground">
                    Forensic analysis found strong evidence of AI generation or heavy manipulation.
                    Content with a high tampering score cannot be registered as original work.
                  </p>
                )}
              </div>

              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={resetForm}>
                  Try a different file
                </Button>
                <Button variant="hero" className="flex-1" onClick={() => window.location.href = "/verify"}>
                  Verify instead
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