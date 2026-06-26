import { create } from "zustand";
import { toast } from "sonner";
import { api, ServiceMeta, GeneratedTemplate } from "@/api/client";

export type TabId = "compose" | "options" | "template";
export type IconMethod = "url" | "github";

export const CATEGORIES = [
  "MediaServer",
  "Downloaders",
  "Tools",
  "Backup",
  "Cloud",
  "Productivity",
  "HomeAutomation",
  "Security",
  "Development",
  "GameServers",
  "Other",
];

export const NO_PORT = "No seleccionar puerto";
export const NO_IMAGE = "No seleccionar imagen";

export interface ServiceConfig {
  included: boolean;
  iconMethod: IconMethod;
  externalIconUrl: string;
  githubRepoIconUrl: string;
  githubImages: string[];
  selectedGithubImage: string;
  previewIconUrl: string;
  description: string;
  supportUrl: string;
  projectUrl: string;
  category: string;
  webPort: string;
}

interface RepoDefaults {
  projectUrl: string;
  supportUrl: string;
  repoIconUrl: string;
  description: string;
}

function makeDefaultConfig(defaults: RepoDefaults): ServiceConfig {
  return {
    included: true,
    iconMethod: defaults.repoIconUrl ? "github" : "url",
    externalIconUrl: "",
    githubRepoIconUrl: defaults.repoIconUrl,
    githubImages: [],
    selectedGithubImage: "",
    previewIconUrl: "",
    description: defaults.description,
    supportUrl: defaults.supportUrl,
    projectUrl: defaults.projectUrl,
    category: "",
    webPort: NO_PORT,
  };
}

function iconUrlOf(c: ServiceConfig): string {
  if (c.iconMethod === "url" && c.externalIconUrl) return c.externalIconUrl;
  if (c.iconMethod === "github" && c.selectedGithubImage) return c.selectedGithubImage;
  return "";
}

function triggerDownload(content: BlobPart, filename: string, type: string) {
  const blob = content instanceof Blob ? content : new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

interface AppState {
  // Navegación
  activeTab: TabId;

  // Compose
  dockerComposeText: string;
  githubRepoUrl: string;
  hasLoadedDockerCompose: boolean;
  isLoadingCompose: boolean;
  foundComposeBranch: string;
  foundComposeDirectory: string;
  foundComposeFilename: string;
  hostPathsToAppdata: boolean;
  composeBackup: string;

  // Defaults a nivel repo (semilla de cada servicio)
  repoDefaults: RepoDefaults;

  // Servicios y su configuración
  services: ServiceMeta[];
  serviceConfigs: Record<string, ServiceConfig>;
  activeServiceKey: string;

  // Resultado
  templates: GeneratedTemplate[];
  activeTemplateKey: string;

  // Setters simples (campos del tab compose)
  set: <K extends keyof AppState>(key: K, value: AppState[K]) => void;

  // Acciones generales
  setActiveTab: (tab: TabId) => void;
  resetApp: () => void;
  loadFromGithub: () => Promise<void>;
  uploadComposeFile: (content: string) => Promise<void>;
  toggleAppdataPaths: (enabled: boolean) => Promise<void>;
  goNext: () => Promise<void>;
  goPrev: () => void;

  // Acciones por servicio (sobre el servicio activo)
  setActiveServiceKey: (key: string) => void;
  updateActiveConfig: (patch: Partial<ServiceConfig>) => void;
  toggleServiceIncluded: (key: string) => void;
  setIconMethod: (m: IconMethod) => void;
  setExternalIconUrl: (url: string) => void;
  setGithubRepoIconUrl: (url: string) => void;
  selectGithubImage: (image: string) => void;
  searchGithubImages: () => Promise<void>;
  previewIcon: () => Promise<void>;

  // Plantillas
  generateTemplates: () => Promise<boolean>;
  setActiveTemplateKey: (key: string) => void;
  updateTemplateXml: (key: string, xml: string) => void;
  downloadOne: (key: string) => void;
  saveOne: (key: string) => Promise<void>;
  downloadAllZip: () => Promise<void>;
  saveAllUnraid: () => Promise<void>;
}

const emptyRepoDefaults: RepoDefaults = {
  projectUrl: "",
  supportUrl: "",
  repoIconUrl: "",
  description: "",
};

const initialState = {
  activeTab: "compose" as TabId,
  dockerComposeText: "",
  githubRepoUrl: "",
  hasLoadedDockerCompose: false,
  isLoadingCompose: false,
  foundComposeBranch: "",
  foundComposeDirectory: "",
  foundComposeFilename: "",
  hostPathsToAppdata: false,
  composeBackup: "",
  repoDefaults: { ...emptyRepoDefaults },
  services: [] as ServiceMeta[],
  serviceConfigs: {} as Record<string, ServiceConfig>,
  activeServiceKey: "",
  templates: [] as GeneratedTemplate[],
  activeTemplateKey: "",
};

export const useAppStore = create<AppState>((setState, getState) => ({
  ...initialState,

  set: (key, value) => setState({ [key]: value } as Partial<AppState>),

  setActiveTab: (tab) => setState({ activeTab: tab }),

  resetApp: () => {
    setState({
      ...initialState,
      repoDefaults: { ...emptyRepoDefaults },
      services: [],
      serviceConfigs: {},
      templates: [],
    });
    toast.success("Todos los campos han sido reiniciados.");
  },

  loadFromGithub: async () => {
    const { githubRepoUrl } = getState();
    if (!githubRepoUrl) {
      toast.error("Por favor, introduce la URL de un repositorio válido.");
      return;
    }
    setState({
      ...initialState,
      repoDefaults: { ...emptyRepoDefaults },
      services: [],
      serviceConfigs: {},
      templates: [],
      githubRepoUrl,
      isLoadingCompose: true,
    });
    try {
      const r = await api.loadFromGithub(githubRepoUrl);
      if (!r.success) {
        toast.error(r.message || "No se encontró un Docker Compose válido.");
        return;
      }
      setState({
        dockerComposeText: r.compose_text,
        hasLoadedDockerCompose: true,
        foundComposeBranch: r.branch,
        foundComposeDirectory: r.directory,
        foundComposeFilename: r.filename,
        repoDefaults: {
          projectUrl: r.project_url,
          supportUrl: r.support_url,
          repoIconUrl: r.repo_icon_url,
          description: r.description,
        },
      });
      toast.success(r.message);
    } catch (e) {
      toast.error(`Error al cargar desde GitHub: ${(e as Error).message}`);
    } finally {
      setState({ isLoadingCompose: false });
    }
  },

  uploadComposeFile: async (content) => {
    try {
      const r = await api.validateCompose(content);
      if (r.valid) {
        setState({ dockerComposeText: content });
        toast.success("Archivo Docker Compose válido cargado correctamente.");
      } else {
        toast.error(r.message);
      }
    } catch (e) {
      toast.error(`Error al cargar el archivo: ${(e as Error).message}`);
    }
  },

  toggleAppdataPaths: async (enabled) => {
    const { dockerComposeText, composeBackup } = getState();
    if (enabled) {
      if (!dockerComposeText) {
        toast.error("No se ha cargado un Docker Compose válido.");
        return;
      }
      try {
        const r = await api.appdataPaths(dockerComposeText);
        setState({
          composeBackup: dockerComposeText,
          dockerComposeText: r.compose_text,
          hostPathsToAppdata: true,
        });
        toast.success("Host paths cambiados a /mnt/user/appdata.");
      } catch (e) {
        toast.error(`Error al cambiar los host paths: ${(e as Error).message}`);
      }
    } else {
      setState({
        dockerComposeText: composeBackup || dockerComposeText,
        composeBackup: "",
        hostPathsToAppdata: false,
      });
      toast.info("Host paths originales restaurados.");
    }
  },

  goNext: async () => {
    const { activeTab, dockerComposeText } = getState();
    if (activeTab === "compose") {
      if (!dockerComposeText) {
        toast.error("Introduce el contenido del Docker Compose antes de continuar.");
        return;
      }
      try {
        const r = await api.composeServices(dockerComposeText);
        if (!r.valid) {
          toast.error(r.message);
          return;
        }
        const st = getState();
        // Defaults del repo (de loadFromGithub) o deducidos de la imagen
        const defaults: RepoDefaults = { ...st.repoDefaults };
        if (!defaults.projectUrl && !defaults.supportUrl && !defaults.repoIconUrl && r.github_urls) {
          defaults.projectUrl = r.github_urls.project_url;
          defaults.supportUrl = r.github_urls.support_url;
          defaults.repoIconUrl = r.github_urls.repo_icon_url;
        }

        // Conservar config previa por servicio si ya existía (no perder ediciones)
        const prev = st.serviceConfigs;
        const configs: Record<string, ServiceConfig> = {};
        for (const svc of r.services) {
          const base = prev[svc.key] ?? makeDefaultConfig(defaults);
          // Ajustar webPort si el seleccionado ya no existe
          const ports = svc.ports;
          const webPort =
            base.webPort && (base.webPort === NO_PORT || ports.includes(base.webPort))
              ? base.webPort
              : NO_PORT;
          configs[svc.key] = { ...base, webPort };
        }

        setState({
          services: r.services,
          serviceConfigs: configs,
          activeServiceKey: r.services[0]?.key ?? "",
          repoDefaults: defaults,
          hasLoadedDockerCompose: true,
          activeTab: "options",
        });
        toast.success("Docker Compose procesado correctamente.");

        // Cargar imágenes del repo para el servicio activo (compartibles)
        const activeKey = r.services[0]?.key ?? "";
        const activeCfg = configs[activeKey];
        if (activeCfg && activeCfg.githubRepoIconUrl && activeCfg.githubImages.length === 0) {
          try {
            const imgs = await api.githubImages(activeCfg.githubRepoIconUrl);
            if (imgs.images.length) {
              getState().updateActiveConfig({ githubImages: [NO_IMAGE, ...imgs.images] });
            }
          } catch {
            /* silencioso */
          }
        }
      } catch (e) {
        toast.error(`Error al procesar el Docker Compose: ${(e as Error).message}`);
      }
    } else if (activeTab === "options") {
      const ok = await getState().generateTemplates();
      if (ok) {
        setState({ activeTab: "template" });
        toast.success("Plantillas generadas correctamente.");
      }
    }
  },

  goPrev: () => {
    const { activeTab } = getState();
    if (activeTab === "options") setState({ activeTab: "compose" });
    else if (activeTab === "template") setState({ activeTab: "options" });
  },

  // --- Por servicio ---------------------------------------------------------

  setActiveServiceKey: (key) => setState({ activeServiceKey: key }),

  updateActiveConfig: (patch) => {
    const { activeServiceKey, serviceConfigs } = getState();
    const current = serviceConfigs[activeServiceKey];
    if (!current) return;
    setState({
      serviceConfigs: { ...serviceConfigs, [activeServiceKey]: { ...current, ...patch } },
    });
  },

  toggleServiceIncluded: (key) => {
    const { serviceConfigs } = getState();
    const current = serviceConfigs[key];
    if (!current) return;
    setState({
      serviceConfigs: { ...serviceConfigs, [key]: { ...current, included: !current.included } },
    });
  },

  setIconMethod: (m) => getState().updateActiveConfig({ iconMethod: m, previewIconUrl: "" }),

  setExternalIconUrl: (url) =>
    getState().updateActiveConfig({ externalIconUrl: url, previewIconUrl: "" }),

  setGithubRepoIconUrl: (url) =>
    getState().updateActiveConfig({
      githubRepoIconUrl: url,
      githubImages: [],
      selectedGithubImage: "",
      previewIconUrl: "",
    }),

  selectGithubImage: (image) => {
    if (image === NO_IMAGE) {
      getState().updateActiveConfig({ selectedGithubImage: "", previewIconUrl: "" });
    } else {
      getState().updateActiveConfig({ selectedGithubImage: image, previewIconUrl: image });
    }
  },

  searchGithubImages: async () => {
    const { activeServiceKey, serviceConfigs } = getState();
    const cfg = serviceConfigs[activeServiceKey];
    if (!cfg?.githubRepoIconUrl) {
      toast.error("Por favor, introduce una URL de GitHub válida.");
      return;
    }
    try {
      const r = await api.githubImages(cfg.githubRepoIconUrl);
      if (r.images.length) {
        getState().updateActiveConfig({ githubImages: [NO_IMAGE, ...r.images] });
        toast.success(r.message);
      } else {
        toast.error(r.message);
      }
    } catch (e) {
      toast.error(`Error al buscar imágenes: ${(e as Error).message}`);
    }
  },

  previewIcon: async () => {
    const { activeServiceKey, serviceConfigs } = getState();
    const cfg = serviceConfigs[activeServiceKey];
    if (!cfg?.externalIconUrl) {
      toast.error("Por favor, introduce una URL de icono válida.");
      return;
    }
    try {
      const r = await api.iconPreview(cfg.externalIconUrl);
      if (r.valid) {
        getState().updateActiveConfig({ previewIconUrl: cfg.externalIconUrl });
        toast.success("Vista previa del icono cargada.");
      } else {
        getState().updateActiveConfig({ previewIconUrl: "" });
        toast.error(r.message);
      }
    } catch {
      getState().updateActiveConfig({ previewIconUrl: "" });
      toast.error("No se encontró imagen en esa URL o no es válida.");
    }
  },

  // --- Plantillas -----------------------------------------------------------

  generateTemplates: async () => {
    const s = getState();
    const included = s.services.filter((svc) => s.serviceConfigs[svc.key]?.included);
    if (!included.length) {
      toast.error("Selecciona al menos un servicio para generar la plantilla.");
      return false;
    }
    const payloadServices = included.map((svc) => {
      const c = s.serviceConfigs[svc.key];
      const icon = iconUrlOf(c);
      return {
        key: svc.key,
        icon_url: icon,
        description: c.description,
        web_port: c.webPort,
        app_fields: {
          Icon: icon,
          Overview: c.description,
          Support: c.supportUrl,
          Project: c.projectUrl,
          Category: c.category,
        },
      };
    });

    try {
      const r = await api.generate({
        compose_content: s.dockerComposeText,
        services: payloadServices,
      });
      if (!r.success || !r.templates.length) {
        toast.error(r.message || "No se pudo generar ninguna plantilla.");
        return false;
      }
      setState({ templates: r.templates, activeTemplateKey: r.templates[0].key });
      return true;
    } catch (e) {
      toast.error(`Error al generar las plantillas: ${(e as Error).message}`);
      return false;
    }
  },

  setActiveTemplateKey: (key) => setState({ activeTemplateKey: key }),

  updateTemplateXml: (key, xml) => {
    const { templates } = getState();
    setState({
      templates: templates.map((t) => (t.key === key ? { ...t, xml } : t)),
    });
  },

  downloadOne: (key) => {
    const t = getState().templates.find((x) => x.key === key);
    if (!t) return;
    triggerDownload(t.xml, t.filename, "application/xml");
  },

  saveOne: async (key) => {
    const t = getState().templates.find((x) => x.key === key);
    if (!t) return;
    try {
      const r = await api.saveLocal([{ filename: t.filename, xml_content: t.xml }]);
      r.success ? toast.success(r.message) : toast.error(r.message);
    } catch (e) {
      toast.error(`Error al guardar la plantilla: ${(e as Error).message}`);
    }
  },

  downloadAllZip: async () => {
    const { templates } = getState();
    if (!templates.length) return;
    try {
      const blob = await api.downloadZip(
        templates.map((t) => ({ filename: t.filename, xml_content: t.xml }))
      );
      triggerDownload(blob, "unraid-templates.zip", "application/zip");
    } catch (e) {
      toast.error(`Error al descargar el ZIP: ${(e as Error).message}`);
    }
  },

  saveAllUnraid: async () => {
    const { templates } = getState();
    if (!templates.length) return;
    try {
      const r = await api.saveLocal(
        templates.map((t) => ({ filename: t.filename, xml_content: t.xml }))
      );
      r.success ? toast.success(r.message) : toast.error(r.message);
    } catch (e) {
      toast.error(`Error al guardar las plantillas: ${(e as Error).message}`);
    }
  },
}));
