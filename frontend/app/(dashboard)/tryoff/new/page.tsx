"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ImageDropzone } from "@/components/tryoff/image-dropzone";
import { GarmentChips } from "@/components/tryoff/garment-chips";
import { submitBatchJobs, uploadTryoffSourceImage, GarmentType } from "@/lib/api/tryoff";

export default function TryoffNewPage() {
  const router = useRouter();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);

  const canSubmit = Boolean(selectedFile && selectedTypes.size > 0) && !isSubmitting;

  const handleFileSelected = useCallback((file: File, previewUrl: string) => {
    setSelectedFile(file);
    setPreviewUrl(previewUrl);
  }, []);

  const handleClearImage = useCallback(() => {
    setSelectedFile(null);
    setPreviewUrl(null);
  }, []);

  const handleToggleType = useCallback((type: GarmentType) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!canSubmit || !selectedFile) return;

    setIsSubmitting(true);
    setUploadProgress(0);

    try {
      // Step 1: Upload TryOff source image (tryoff_source_images, not prendas)
      setUploadProgress(10);
      const uploaded = await uploadTryoffSourceImage(selectedFile);
      setUploadProgress(100);

      // Step 2: Submit batch jobs
      const result = await submitBatchJobs({
        source_image_id: uploaded.id,
        garment_types: [...selectedTypes] as GarmentType[],
      });

      const jobIds = result.jobs.map((j) => j.job_id);

      toast.success(`${jobIds.length} extraction job(s) started`);

      router.push(`/tryoff/status?job_ids=${jobIds.join(",")}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Error starting extraction";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
      setUploadProgress(null);
    }
  }, [canSubmit, selectedFile, selectedTypes, router]);

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Extract Garments from Image</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload a photo, select garment types, and start extraction
        </p>
      </div>

      {/* Step 1: Image Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">1. Source Image</CardTitle>
          <CardDescription>
            Upload a photo of a model wearing the garments you want to extract
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ImageDropzone
            onFileSelected={handleFileSelected}
            onClear={handleClearImage}
            selectedFile={selectedFile}
            previewUrl={previewUrl}
          />
        </CardContent>
      </Card>

      {/* Step 2: Garment Type Selection + Submit */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">2. Select Garment Types</CardTitle>
          <CardDescription>
            Choose which garments to extract from the image (multiple allowed)
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <GarmentChips selected={selectedTypes} onToggle={handleToggleType} />

          {uploadProgress !== null && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Uploading image...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <Button
            className="w-full"
            size="lg"
            disabled={!canSubmit}
            onClick={handleSubmit}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Starting extraction...
              </>
            ) : (
              "Start Extraction"
            )}
          </Button>

          {!canSubmit && !isSubmitting && (
            <p className="text-xs text-muted-foreground text-center">
              {!selectedFile && "Upload a source image"}
              {selectedFile && selectedTypes.size === 0 && "Select at least one garment type"}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
