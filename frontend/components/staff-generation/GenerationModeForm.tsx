'use client';

import { useEffect, useId, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { GarmentUploader } from '@/components/vton/GarmentUploader';
import { ModelPosePicker } from '@/components/model-pose/ModelPosePicker';
import { ClothTypeSelector } from '@/components/vton/ClothTypeSelector';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { GenerationMode, GenerationProvider } from '@/lib/api/image-generation';
import { listSelectableTemplates, type ImageTemplate } from '@/lib/api/templates';
import {
  validateGenerationForm,
  type GenerationFormValues,
} from '@/lib/staff-generation/validate-generation-form';

const MODE_LABELS: Record<GenerationMode, string> = {
  try_on: 'Prendas sobre modelo',
  text: 'Desde texto',
  edit: 'Edición',
  extraction: 'Extracción',
};

interface GenerationModeFormProps {
  wholesalerId: string;
  defaultSku?: string | null;
  onSubmit: (values: GenerationFormValues) => Promise<void>;
  isSubmitting: boolean;
}

function emptyValues(mode: GenerationMode): GenerationFormValues {
  return {
    mode,
    provider: 'openai',
    prompt: '',
    garmentId: null,
    modelId: null,
    clothType: null,
    referenceImageIds: [],
  };
}

export function GenerationModeForm({
  wholesalerId,
  defaultSku,
  onSubmit,
  isSubmitting,
}: GenerationModeFormProps) {
  const promptId = useId();
  const templateId = useId();
  const [mode, setMode] = useState<GenerationMode>('try_on');
  const [values, setValues] = useState<GenerationFormValues>(() => {
    const initial = emptyValues('try_on');
    if (defaultSku) {
      initial.prompt = `SKU ${defaultSku}`;
    }
    return initial;
  });
  const [templates, setTemplates] = useState<ImageTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!wholesalerId) return;
    listSelectableTemplates(wholesalerId)
      .then(setTemplates)
      .catch(() => setTemplates([]));
  }, [wholesalerId]);

  const handleModeChange = (nextMode: string) => {
    const typed = nextMode as GenerationMode;
    const next = emptyValues(typed);
    if (defaultSku && (typed === 'text' || typed === 'edit')) {
      next.prompt = `SKU ${defaultSku}`;
    }
    setMode(typed);
    setValues(next);
    setSelectedTemplateId('');
    setError(null);
  };

  const applyTemplate = (id: string) => {
    setSelectedTemplateId(id);
    const template = templates.find((item) => item.id === id);
    if (!template) return;
    setValues((current) => ({
      ...current,
      prompt: template.prompt ?? current.prompt,
    }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const message = validateGenerationForm(values);
    if (message) {
      setError(message);
      return;
    }
    setError(null);
    await onSubmit(values);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6" noValidate>
      <Tabs value={mode} onValueChange={handleModeChange}>
        <TabsList className="flex h-auto min-h-11 w-full flex-wrap" aria-label="Modo de generación">
          {(Object.keys(MODE_LABELS) as GenerationMode[]).map((item) => (
            <TabsTrigger key={item} value={item} className="min-h-11 flex-1">
              {MODE_LABELS[item]}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value={mode} className="mt-4 space-y-5">
          <ModeFields
            key={mode}
            values={values}
            onChange={setValues}
            promptId={promptId}
          />
        </TabsContent>
      </Tabs>

      {mode === 'try_on' ? (
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">Proveedor</legend>
          <RadioGroup
            value={values.provider}
            onValueChange={(value) =>
              setValues((current) => ({ ...current, provider: value as GenerationProvider }))
            }
            className="flex flex-wrap gap-4"
            aria-label="Proveedor de generación"
          >
            <div className="flex min-h-11 items-center gap-2">
              <RadioGroupItem value="openai" id="provider-openai" />
              <Label htmlFor="provider-openai">OpenAI</Label>
            </div>
            <div className="flex min-h-11 items-center gap-2">
              <RadioGroupItem value="vton" id="provider-vton" />
              <Label htmlFor="provider-vton">VTON existente</Label>
            </div>
          </RadioGroup>
        </fieldset>
      ) : (
        <p className="text-sm text-muted-foreground">
          Este modo usa OpenAI. El proveedor no se cambia en silencio.
        </p>
      )}

      {templates.length > 0 && (
        <div className="space-y-2">
          <Label htmlFor={templateId}>Plantilla (opcional)</Label>
          <select
            id={templateId}
            className="h-11 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            value={selectedTemplateId}
            onChange={(event) => applyTemplate(event.target.value)}
          >
            <option value="">Sin plantilla</option>
            {templates.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name} ({template.scope}, v{template.version})
              </option>
            ))}
          </select>
        </div>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertTitle>No se envió el trabajo</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button type="submit" className="min-h-11 min-w-44" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" />}
        Iniciar generación
      </Button>
    </form>
  );
}

function ModeFields({
  values,
  onChange,
  promptId,
}: {
  values: GenerationFormValues;
  onChange: (values: GenerationFormValues) => void;
  promptId: string;
}) {
  if (values.mode === 'try_on') {
    return (
      <div className="space-y-5">
        <div className="space-y-2">
          <Label>Fotografía de la prenda</Label>
          <GarmentUploader
            uploadedId={values.garmentId}
            onUploaded={(garmentId) => onChange({ ...values, garmentId })}
            onClear={() => onChange({ ...values, garmentId: null })}
          />
        </div>
        <div className="space-y-2">
          <Label>Modelo</Label>
          <ModelPosePicker
            selectedId={values.modelId}
            onSelected={(selection) =>
              onChange({ ...values, modelId: selection.modelPhotoId })
            }
          />
        </div>
        <div className="space-y-2">
          <Label>Tipo de prenda</Label>
          <ClothTypeSelector
            selected={values.clothType as 'upper_body' | 'lower_body' | 'dress' | null}
            onSelected={(clothType) => onChange({ ...values, clothType })}
          />
        </div>
      </div>
    );
  }

  const needsPrompt = values.mode === 'text' || values.mode === 'edit';
  const needsReferences = values.mode === 'edit' || values.mode === 'extraction';

  return (
    <div className="space-y-5">
      {needsPrompt && (
        <div className="space-y-2">
          <Label htmlFor={promptId}>
            {values.mode === 'edit' ? 'Instrucciones de edición' : 'Prompt'}
          </Label>
          <textarea
            id={promptId}
            required
            rows={4}
            className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            value={values.prompt}
            onChange={(event) => onChange({ ...values, prompt: event.target.value })}
          />
        </div>
      )}
      {needsReferences && (
        <div className="space-y-2">
          <Label>Imágenes de referencia</Label>
          <GarmentUploader
            onUploaded={(id) =>
              onChange({ ...values, referenceImageIds: [...values.referenceImageIds, id] })
            }
          />
          {values.referenceImageIds.length > 0 && (
            <ul className="text-sm text-muted-foreground">
              {values.referenceImageIds.map((id) => (
                <li key={id}>Referencia {id.slice(0, 8)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
