import { useState } from "react";
import Editor from "@monaco-editor/react";
import { ChevronDown, Download } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function TemplateTab() {
  const {
    templates,
    activeTemplateKey,
    setActiveTemplateKey,
    updateTemplateXml,
    goPrev,
    downloadOne,
    saveOne,
    downloadAllZip,
    saveAllUnraid,
  } = useAppStore();
  const [menuOpen, setMenuOpen] = useState(false);
  const isDark = document.documentElement.classList.contains("dark");

  const active = templates.find((t) => t.key === activeTemplateKey) ?? templates[0];
  const multiple = templates.length > 1;

  const closeAnd = (fn: () => void) => () => {
    fn();
    setMenuOpen(false);
  };

  return (
    <div className="flex h-full flex-col">
      {/* Sub-tabs: una por XML generado */}
      {multiple && (
        <div className="mb-3 flex flex-wrap gap-2">
          {templates.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setActiveTemplateKey(t.key)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                t.key === active?.key
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-input hover:bg-accent"
              )}
            >
              {t.container_name}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-hidden rounded-lg border">
        <Editor
          height="100%"
          defaultLanguage="xml"
          theme={isDark ? "vs-dark" : "light"}
          path={active?.key}
          value={active?.xml ?? ""}
          onChange={(v) => active && updateTemplateXml(active.key, v ?? "")}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            scrollBeyondLastLine: false,
            wordWrap: "on",
          }}
        />
      </div>

      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={goPrev}>
          Anterior
        </Button>
        <div className="relative">
          <Button onClick={() => setMenuOpen((o) => !o)}>
            <Download size={16} />
            Descargar Plantilla
            <ChevronDown size={16} />
          </Button>
          {menuOpen && (
            <div className="absolute bottom-full right-0 z-10 mb-1 w-72 rounded-md border bg-popover p-1 shadow-md">
              <div className="px-3 pb-1 pt-2 text-xs font-semibold text-muted-foreground">
                {multiple ? `Este XML (${active?.container_name})` : "Este XML"}
              </div>
              <button
                className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-accent"
                onClick={closeAnd(() => active && downloadOne(active.key))}
              >
                En el equipo local
              </button>
              <button
                className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-accent"
                onClick={closeAnd(() => active && saveOne(active.key))}
              >
                En la carpeta de plantillas Unraid
              </button>

              {multiple && (
                <>
                  <div className="mt-1 border-t px-3 pb-1 pt-2 text-xs font-semibold text-muted-foreground">
                    Todos los XML ({templates.length})
                  </div>
                  <button
                    className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-accent"
                    onClick={closeAnd(downloadAllZip)}
                  >
                    En el equipo local (ZIP)
                  </button>
                  <button
                    className="block w-full rounded px-3 py-2 text-left text-sm hover:bg-accent"
                    onClick={closeAnd(saveAllUnraid)}
                  >
                    En la carpeta de plantillas Unraid
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
