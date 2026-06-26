import { useRef, useState } from "react";
import { Loader2, Upload } from "lucide-react";
import { toast } from "sonner";
import { useAppStore } from "@/store/useAppStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { InfoHover } from "@/components/InfoHover";

const PLACEHOLDER = `services:
  miapp:
    image: usuario/miapp:latest
    container_name: miapp
    environment:
      - TZ=Europe/Madrid
    ports:
      - 8080:80
    volumes:
      - /mnt/user/appdata/miapp:/config`;

export function ComposeTab() {
  const {
    dockerComposeText,
    githubRepoUrl,
    isLoadingCompose,
    foundComposeBranch,
    foundComposeDirectory,
    foundComposeFilename,
    hostPathsToAppdata,
    set,
    resetApp,
    goNext,
    loadFromGithub,
    uploadComposeFile,
    toggleAppdataPaths,
  } = useAppStore();
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const hasVolumes = /^[ \t]*volumes[ \t]*:/m.test(dockerComposeText);

  const handleFile = (file: File) => {
    if (!/\.(ya?ml)$/i.test(file.name)) {
      toast.error("El archivo debe ser .yml o .yaml");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => uploadComposeFile(String(reader.result));
    reader.readAsText(file);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-4">
      <Label className="text-base">Introduce el contenido del Docker Compose</Label>
      <Textarea
        className="h-[28rem] font-mono text-sm"
        placeholder={PLACEHOLDER}
        value={dockerComposeText}
        onChange={(e) => set("dockerComposeText", e.target.value)}
      />

      <div
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
          dragOver ? "border-primary bg-accent" : "border-input"
        }`}
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
        }}
      >
        <Upload className="mb-2 text-muted-foreground" />
        <span className="text-sm text-muted-foreground">
          Arrastra tu docker-compose (.yml / .yaml) o haz clic para seleccionarlo
        </span>
        <input
          ref={fileRef}
          type="file"
          accept=".yml,.yaml"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>

      <div className="space-y-2 rounded-lg border p-4">
        <Label>
          Cargar desde un repositorio de GitHub
          <InfoHover text="Pega la URL de un repositorio de GitHub. Se buscará el docker-compose en rutas comunes, el README y, si hace falta, en todo el árbol del repo." />
        </Label>
        <div className="flex gap-2">
          <Input
            placeholder="https://github.com/usuario/repositorio"
            value={githubRepoUrl}
            onChange={(e) => set("githubRepoUrl", e.target.value)}
          />
          <Button onClick={loadFromGithub} disabled={isLoadingCompose}>
            {isLoadingCompose && <Loader2 className="animate-spin" size={16} />}
            Cargar Compose
          </Button>
        </div>
        <div className="flex items-center gap-2 pt-1">
          <Switch
            checked={hostPathsToAppdata}
            onCheckedChange={toggleAppdataPaths}
            disabled={!hasVolumes}
          />
          <span
            className={`text-sm ${hasVolumes ? "text-muted-foreground" : "text-muted-foreground/50"}`}
          >
            Cambiar todos los host paths a /mnt/user/appdata
          </span>
          <InfoHover text="Cuidado!!! esto sustituye todas las rutas host del compose a: <b>/mnt/user/appdata/&lt;nombre_contenedor&gt;&lt;ruta_contenedor&gt;</b>, asegúrate que todas las rutas son correctas. Desactívalo para restaurar el original." />
        </div>
        {foundComposeFilename && (
          <p className="text-sm text-muted-foreground">
            Encontrado en rama <b>{foundComposeBranch}</b>
            {foundComposeDirectory && (
              <>
                , directorio <b>{foundComposeDirectory || "/"}</b>
              </>
            )}
            , archivo <b>{foundComposeFilename}</b>
          </p>
        )}
      </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={resetApp}>
          Limpiar
        </Button>
        <Button onClick={goNext}>Siguiente</Button>
      </div>
    </div>
  );
}
