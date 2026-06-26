import { Toaster } from "sonner";
import { useAppStore } from "@/store/useAppStore";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ComposeTab } from "@/components/tabs/ComposeTab";
import { OptionsTab } from "@/components/tabs/OptionsTab";
import { TemplateTab } from "@/components/tabs/TemplateTab";

export default function App() {
  const { activeTab } = useAppStore();
  const isDark = document.documentElement.classList.contains("dark");

  return (
    <div className="mx-auto min-h-screen max-w-4xl px-4">
      <Header />
      {/* Las pestañas son solo un indicador del paso actual; la navegación
          se hace con los botones "Anterior" / "Siguiente". */}
      <Tabs value={activeTab}>
        <div className="flex justify-center pt-2">
          <TabsList>
            <TabsTrigger value="compose" className="pointer-events-none select-none">
              Docker Compose
            </TabsTrigger>
            <TabsTrigger value="options" className="pointer-events-none select-none">
              Opciones Plantilla
            </TabsTrigger>
            <TabsTrigger value="template" className="pointer-events-none select-none">
              Plantilla Unraid
            </TabsTrigger>
          </TabsList>
        </div>

        <Card className="mt-6">
          {/* Altura fija: la tarjeta no cambia de alto entre pestañas.
              Cada pestaña ocupa toda la altura (h-full) para anclar sus
              botones de navegación al fondo. */}
          <CardContent className="h-[920px]">
            <TabsContent value="compose" className="mt-0 h-full">
              <ComposeTab />
            </TabsContent>
            <TabsContent value="options" className="mt-0 h-full">
              <OptionsTab />
            </TabsContent>
            <TabsContent value="template" className="mt-0 h-full">
              <TemplateTab />
            </TabsContent>
          </CardContent>
        </Card>
      </Tabs>
      <Footer />
      <Toaster richColors theme={isDark ? "dark" : "light"} position="top-center" />
    </div>
  );
}
