//src/verify.tsx
import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Upload, Search, CheckCircle, AlertTriangle, XCircle, Eye, FileText, Link } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface VerificationResult {
  result: "exact_match" | "near_duplicate" | "not_found" | "error";
  confidence: number;
  match_details?: {
    id: number;
    owner_name: string;
    owner_address?: string;
    registered_at: string;
    tx_hash?: string;
    phash_distance?: number;
    original_tamper_score: number;
  };
  verification_type?: string;
  tampering_analysis?: {
    tamper_probability: number;
    confidence: number;
    detected_artifacts: string[];
    analysis_details?: {
      statistical_score: number;
      artifacts_score: number;
      metadata_score: number;
    };
  };
  potential_theft?: boolean;
  message?: string;
  suggestions?: string[];
}

const Verify = () => {
  const [step, setStep] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [qrCode, setQrCode] = useState("");
  const [results, setResults] = useState<VerificationResult | null>(null);
  const [progress, setProgress] = useState(0);
  const { toast } = useToast();

  const API_BASE = "https://authx-website.onrender.com";

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      toast({
        title: "File uploaded",
        description: `${selectedFile.name} ready for verification.`,
      });
    }
  };

  const handleVerifyByProofId = async (proofId: string) => {
    try {
      const response = await fetch(`${API_BASE}/proof/${proofId}`);
      if (response.ok) {
        const proofData = await response.json();
        return {
          result: "exact_match" as const,
          confidence: 1.0,
          match_details: {
            id: proofData.id,
            owner_name: proofData.owner_name,
            owner_address: proofData.owner_address,
            registered_at: proofData.registered_at,
            tx_hash: proofData.tx_hash,
            original_tamper_score: proofData.tamper_score
          },
          verification_type: "proof_id_lookup",
          message: "Content verified via proof certificate"
        };
      } else {
        throw new Error("Proof certificate not found");
      }
    } catch (error) {
      throw new Error(`Certificate verification failed: ${error}`);
    }
  };

  const handleVerifyByFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/verify`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      throw new Error(`File verification failed: ${error}`);
    }
  };

  const handleVerify = async () => {
    if (!file && !qrCode) {
      toast({
        title: "No input provided",
        description: "Please upload a file or enter a certificate ID.",
        variant: "destructive"
      });
      return;
    }

    setIsProcessing(true);
    setStep(2);
    setProgress(0);

    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 300);

      let verificationResult: VerificationResult;

      if (qrCode) {
        // Verify by proof/certificate ID
        toast({
          title: "Verifying certificate...",
          description: "Looking up proof certificate in database",
        });
        verificationResult = await handleVerifyByProofId(qrCode);
      } else if (file) {
        // Verify by file upload
        toast({
          title: "Analyzing file...",
          description: "Running multi-layer detection pipeline",
        });
        verificationResult = await handleVerifyByFile(file);
      } else {
        throw new Error("No verification method available");
      }

      clearInterval(progressInterval);
      setProgress(100);

      await new Promise(resolve => setTimeout(resolve, 500)); // Brief pause for UX

      setResults(verificationResult);
      setStep(3);

      // Success toast based on result
      if (verificationResult.result === "exact_match") {
        toast({
          title: "Content Verified!",
          description: "Exact match found in database",
        });
      } else if (verificationResult.result === "near_duplicate") {
        toast({
          title: "Similar Content Found",
          description: "Potential modification detected",
          variant: "warning"
        });
      } else {
        toast({
          title: "No Match Found",
          description: "Content not found in database",
        });
      }

    } catch (error) {
      toast({
        title: "Verification Failed",
        description: error instanceof Error ? error.message : "An unknown error occurred",
        variant: "destructive"
      });
      setStep(1);
    } finally {
      setIsProcessing(false);
      setProgress(0);
    }
  };

  const getStatusInfo = (result: VerificationResult) => {
    switch (result.result) {
      case "exact_match":
        return {
          color: "success",
          icon: <CheckCircle className="text-green-500" />,
          title: "✅ Content Verified",
          description: "This content matches exactly with registered original"
        };
      case "near_duplicate":
        return {
          color: "warning",
          icon: <AlertTriangle className="text-yellow-500" />,
          title: "⚠️ Similar Content Found",
          description: "Content appears to be modified version of registered work"
        };
      case "not_found":
        return {
          color: "secondary",
          icon: <XCircle className="text-gray-500" />,
          title: "❓ Content Not Found",
          description: "No matching content found in database"
        };
      default:
        return {
          color: "destructive",
          icon: <XCircle className="text-red-500" />,
          title: "❌ Verification Error",
          description: result.message || "An error occurred during verification"
        };
    }
  };

  const formatConfidence = (confidence: number) => {
    return Math.round(confidence * 100);
  };

  const formatPhashSimilarity = (distance: number | undefined) => {
    if (distance === undefined) return "N/A";
    // Convert pHash distance to similarity percentage (lower distance = higher similarity)
    const similarity = Math.max(0, Math.round((1 - distance / 64) * 100));
    return `${similarity}%`;
  };

  return (
    <div className="min-h-screen pt-20 pb-16">
      <div className="container mx-auto px-4 max-w-4xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">Verify Content Authenticity</h1>
          <p className="text-xl text-muted-foreground">
            Check if content is original, modified, or stolen using our AI-powered detection system
          </p>
        </div>

        {step === 1 && (
          <Card className="bg-gradient-card shadow-elegant">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="text-primary" />
                Upload Content or Enter Certificate ID
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* File Upload */}
              <div className="space-y-2">
                <Label htmlFor="verify-file">Upload Suspected Content</Label>
                <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-8 text-center hover:border-primary/50 transition-smooth">
                  <input
                    id="verify-file"
                    type="file"
                    onChange={handleFileUpload}
                    className="hidden"
                    accept="image/*,audio/*,.txt,.pdf,.doc,.docx"
                  />
                  <label htmlFor="verify-file" className="cursor-pointer">
                    {file ? (
                      <div className="space-y-2">
                        <CheckCircle className="text-success mx-auto text-3xl" />
                        <p className="font-medium">{file.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {(file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        <Upload className="text-muted-foreground mx-auto text-3xl" />
                        <p>Click to upload content for verification</p>
                        <p className="text-sm text-muted-foreground">
                          Support: Images, Audio, Text, Documents
                        </p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex-1 border-t border-muted-foreground/20"></div>
                <span className="text-sm text-muted-foreground">OR</span>
                <div className="flex-1 border-t border-muted-foreground/20"></div>
              </div>

              {/* Certificate ID */}
              <div className="space-y-2">
                <Label htmlFor="certificate-id">Certificate ID or Proof URL</Label>
                <Input
                  id="certificate-id"
                  value={qrCode}
                  onChange={(e) => setQrCode(e.target.value)}
                  placeholder="Enter certificate ID (e.g., 123) or full proof URL"
                />
                <p className="text-xs text-muted-foreground">
                  You can find the certificate ID in your registration proof
                </p>
              </div>

              <Button 
                onClick={handleVerify} 
                className="w-full" 
                size="lg" 
                variant="accent"
                disabled={isProcessing}
              >
                <Search className="mr-2" />
                Start Verification
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card className="bg-gradient-card shadow-elegant">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="text-primary animate-pulse" />
                Running Verification Pipeline
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-16 w-16 border-4 border-accent border-t-transparent mx-auto mb-4"></div>
                <p className="text-lg font-medium">Analyzing content authenticity...</p>
                <p className="text-muted-foreground">
                  {file ? "Running AI tampering detection and hash analysis" : "Looking up certificate in database"}
                </p>
              </div>
              <Progress value={progress} className="w-full" />
            </CardContent>
          </Card>
        )}

        {step === 3 && results && (
          <div className="space-y-6">
            {/* Main Result */}
            <Card className={`shadow-lg border-2`}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {getStatusInfo(results).icon}
                  Verification Results
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between mb-6">
                  <div className="flex-1">
                    <h3 className="text-2xl font-bold mb-2">
                      {getStatusInfo(results).title}
                    </h3>
                    <p className="text-muted-foreground">
                      {getStatusInfo(results).description}
                    </p>
                  </div>
                  <Badge variant="outline" className="text-lg px-4 py-2">
                    {formatConfidence(results.confidence)}% Confidence
                  </Badge>
                </div>

                {results.match_details && (
                  <div className="grid md:grid-cols-2 gap-6 mb-6">
                    <div className="space-y-4">
                      <h4 className="font-semibold">Original Owner Information</h4>
                      <div className="bg-muted/30 rounded-lg p-4 space-y-2">
                        <p><span className="font-medium">Creator:</span> {results.match_details.owner_name}</p>
                        <p><span className="font-medium">Registered:</span> {new Date(results.match_details.registered_at).toLocaleString()}</p>
                        {results.match_details.tx_hash && (
                          <p className="text-sm">
                            <span className="font-medium">Blockchain Txn:</span>{' '}
                            <span className="font-mono text-xs">{results.match_details.tx_hash}</span>
                          </p>
                        )}
                        {results.match_details.owner_address && (
                          <p className="text-sm">
                            <span className="font-medium">Address:</span>{' '}
                            <span className="font-mono text-xs">{results.match_details.owner_address}</span>
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-4">
                      <h4 className="font-semibold">Detection Pipeline Results</h4>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span>Verification Type:</span>
                          <Badge variant="outline">
                            {results.verification_type === "sha256_exact" && "SHA-256 Exact"}
                            {results.verification_type === "phash_similarity" && "Perceptual Hash"}
                            {results.verification_type === "proof_id_lookup" && "Certificate Lookup"}
                          </Badge>
                        </div>
                        
                        {results.match_details.phash_distance !== undefined && (
                          <div className="flex items-center justify-between">
                            <span>Perceptual Similarity:</span>
                            <Badge variant={
                              results.match_details.phash_distance <= 5 ? "default" :
                              results.match_details.phash_distance <= 15 ? "secondary" : "outline"
                            }>
                              {formatPhashSimilarity(results.match_details.phash_distance)}
                            </Badge>
                          </div>
                        )}

                        <div className="flex items-center justify-between">
                          <span>Original Tamper Score:</span>
                          <Badge variant={
                            results.match_details.original_tamper_score < 0.3 ? "default" :
                            results.match_details.original_tamper_score < 0.7 ? "secondary" : "destructive"
                          }>
                            {Math.round(results.match_details.original_tamper_score * 100)}%
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* AI Tampering Analysis */}
                {results.tampering_analysis && (
                  <div className="mb-6">
                    <h4 className="font-semibold mb-3">AI Forensic Analysis</h4>
                    <div className="bg-muted/30 rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span>Tampering Probability:</span>
                        <Badge variant={
                          results.tampering_analysis.tamper_probability < 0.3 ? "default" :
                          results.tampering_analysis.tamper_probability < 0.7 ? "secondary" : "destructive"
                        }>
                          {Math.round(results.tampering_analysis.tamper_probability * 100)}%
                        </Badge>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span>AI Confidence:</span>
                        <Badge variant="outline">
                          {Math.round(results.tampering_analysis.confidence * 100)}%
                        </Badge>
                      </div>

                      {results.tampering_analysis.detected_artifacts.length > 0 && (
                        <div>
                          <span className="font-medium">Detected Artifacts:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {results.tampering_analysis.detected_artifacts.map((artifact, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {artifact.replace(/_/g, ' ')}
                              </Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Potential Theft Warning */}
                {results.potential_theft && (
                  <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
                    <h4 className="font-semibold text-destructive mb-2">⚠️ Potential Content Theft Detected</h4>
                    <p className="text-sm">
                      This content appears to be a modified version of registered work. 
                      The AI forensics detected significant modifications that suggest tampering.
                    </p>
                  </div>
                )}

                {/* No Match Information */}
                {results.result === "not_found" && results.suggestions && (
                  <div className="mb-6 p-4 bg-muted/30 rounded-lg">
                    <h4 className="font-semibold mb-2">Suggestions</h4>
                    <ul className="text-sm space-y-1">
                      {results.suggestions.map((suggestion, index) => (
                        <li key={index} className="flex items-start gap-2">
                          <span>•</span>
                          <span>{suggestion}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="flex gap-3 pt-4 border-t">
                  <Button 
                    variant="outline" 
                    onClick={() => {
                      setStep(1); 
                      setFile(null); 
                      setQrCode(""); 
                      setResults(null);
                    }}
                  >
                    Verify Another File
                  </Button>
                  
                  {results.match_details && (
                    <Button variant="ghost" asChild>
                      <a 
                        href={`${API_BASE}/proof/${results.match_details.id}`} 
                        target="_blank" 
                        rel="noopener noreferrer"
                      >
                        <Link className="mr-2" size={16} />
                        View Full Proof
                      </a>
                    </Button>
                  )}
                  
                  <Button variant="ghost">
                    <FileText className="mr-2" />
                    Download Report
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Verify;