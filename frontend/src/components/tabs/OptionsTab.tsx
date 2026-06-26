import { useAppStore, CATEGORIES, NO_PORT } from "@/store/useAppStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { InfoHover } from "@/components/InfoHover";
import { cn } from "@/lib/utils";

export function OptionsTab() {
  const s = useAppStore();
  const activeService = s.services.find((svc) => svc.key === s.activeServiceKey);
  const cfg = s.serviceConfigs[s.activeServiceKey];

  const ports = activeService ? [NO_PORT, ...activeService.ports] : [NO_PORT];

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 space-y-5">
        {/* Selector de contenedores (multiservicio) */}
        {s.services.length > 1 && (
          <div className="space-y-2 rounded-lg border p-4">
            <Label className="text-base">
              Contenedores a generar
              <InfoHover text="Cada servicio del compose genera su propia plantilla. Desmarca los que no quieras crear en Unraid (p. ej. una base de datos interna). Haz clic en el nombre para configurar ese contenedor." />
            </Label>
            <div className="flex flex-wrap gap-2">
              {s.services.map((svc) => {
                const c = s.serviceConfigs[svc.key];
                const active = svc.key === s.activeServiceKey;
                return (
                  <div
                    key={svc.key}
                    className={cn(
                      "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors",
                      active ? "border-primary bg-accent" : "border-input",
                      c?.included ? "" : "opacity-50"
                    )}
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 cursor-pointer accent-primary"
                      checked={c?.included ?? true}
                      onChange={() => s.toggleServiceIncluded(svc.key)}
                    />
                    <button
                      type="button"
                      className="cursor-pointer font-medium"
                      onClick={() => s.setActiveServiceKey(svc.key)}
                    >
                      {svc.container_name}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {!cfg ? (
          <p className="text-sm text-muted-foreground">No hay servicios para configurar.</p>
        ) : (
          <>
            {activeService && (
              <p className="text-sm text-muted-foreground">
                Configurando <b className="text-foreground">{activeService.container_name}</b>
                {activeService.image && <> · {activeService.image}</>}
              </p>
            )}

            {/* Icono */}
            <div className="space-y-3 rounded-lg border p-4">
              <Label className="text-base">URL del icono</Label>
              <RadioGroup
                className="flex gap-6"
                value={cfg.iconMethod}
                onValueChange={(v) => s.setIconMethod(v as "url" | "github")}
              >
                <label className="flex items-center gap-2 text-sm">
                  <RadioGroupItem value="url" /> URL externa
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <RadioGroupItem value="github" /> Repositorio
                </label>
              </RadioGroup>

              {cfg.iconMethod === "url" && (
                <div className="flex gap-2">
                  <Input
                    placeholder="https://.../icono.png"
                    value={cfg.externalIconUrl}
                    onChange={(e) => s.setExternalIconUrl(e.target.value)}
                  />
                  <Button variant="secondary" onClick={s.previewIcon}>
                    Obtener
                  </Button>
                </div>
              )}

              {cfg.iconMethod === "github" && (
                <div className="space-y-2">
                  <div className="flex gap-2">
                    <Input
                      placeholder="https://github.com/usuario/repositorio"
                      value={cfg.githubRepoIconUrl}
                      onChange={(e) => s.setGithubRepoIconUrl(e.target.value)}
                    />
                    <Button variant="secondary" onClick={s.searchGithubImages}>
                      Buscar
                    </Button>
                  </div>
                  {cfg.githubImages.length > 0 && (
                    <Select value={cfg.selectedGithubImage} onValueChange={s.selectGithubImage}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona una imagen" />
                      </SelectTrigger>
                      <SelectContent>
                        {cfg.githubImages.map((img) => (
                          <SelectItem key={img} value={img}>
                            {img.startsWith("http") ? img.split("/").pop() : img}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
              )}

              {cfg.previewIconUrl && (
                <img
                  src={cfg.previewIconUrl}
                  alt="Vista previa"
                  className="h-16 w-16 rounded border object-contain"
                />
              )}
            </div>

            {/* Puerto web */}
            <div className="space-y-2">
              <Label>
                Puerto Web para la Interfaz
                <InfoHover text="Puerto que se usará en la etiqueta WebUI de Unraid. Solo afecta al botón de acceso web del contenedor." />
              </Label>
              <Select
                value={cfg.webPort}
                onValueChange={(v) => s.updateActiveConfig({ webPort: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona un puerto" />
                </SelectTrigger>
                <SelectContent>
                  {ports.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Descripción */}
            <div className="space-y-2">
              <Label>Descripción de la plantilla</Label>
              <Textarea
                className="h-20"
                placeholder="Describe brevemente para qué sirve este contenedor"
                value={cfg.description}
                onChange={(e) => s.updateActiveConfig({ description: e.target.value })}
              />
            </div>

            {/* Soporte / Proyecto */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>URL de soporte</Label>
                <Input
                  placeholder="https://github.com/usuario/repo/releases"
                  value={cfg.supportUrl}
                  onChange={(e) => s.updateActiveConfig({ supportUrl: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>URL del proyecto</Label>
                <Input
                  placeholder="https://github.com/usuario/repo"
                  value={cfg.projectUrl}
                  onChange={(e) => s.updateActiveConfig({ projectUrl: e.target.value })}
                />
              </div>
            </div>

            {/* Categoría */}
            <div className="space-y-2">
              <Label>Categoría</Label>
              <Select
                value={cfg.category}
                onValueChange={(v) => s.updateActiveConfig({ category: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecciona una categoría" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c}>
                      {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </>
        )}
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={s.goPrev}>
          Anterior
        </Button>
        <Button onClick={s.goNext}>Siguiente</Button>
      </div>
    </div>
  );
}
