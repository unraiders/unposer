// Cliente de la API. En dev, Vite proxya /api a FastAPI (localhost:8000);
// en producción todo sale del mismo origen.

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Error ${res.status} en ${path}`);
  }
  return res.json() as Promise<T>;
}

export interface GithubUrls {
  project_url: string;
  support_url: string;
  repo_icon_url: string;
}

export interface ServiceMeta {
  key: string;
  container_name: string;
  image: string;
  ports: string[];
}

export interface ServicesResponse {
  valid: boolean;
  message: string;
  services: ServiceMeta[];
  github_urls?: GithubUrls | null;
}

export interface LoadComposeResponse {
  success: boolean;
  compose_text: string;
  branch: string;
  directory: string;
  filename: string;
  project_url: string;
  support_url: string;
  repo_icon_url: string;
  description: string;
  message: string;
}

export interface AppFieldsPayload {
  Icon: string;
  Overview: string;
  Support: string;
  Project: string;
  Category: string;
}

export interface ServiceGenerateConfig {
  key: string;
  icon_url: string;
  description: string;
  web_port: string;
  app_fields: AppFieldsPayload;
}

export interface GeneratedTemplate {
  key: string;
  container_name: string;
  filename: string;
  xml: string;
}

export interface GenerateResponse {
  success: boolean;
  templates: GeneratedTemplate[];
  message: string;
}

export interface SaveItem {
  filename: string;
  xml_content: string;
}

export const api = {
  validateCompose: (content: string) =>
    post<{ valid: boolean; message: string; image?: string }>("/api/compose/validate", {
      content,
    }),
  composeServices: (content: string) =>
    post<ServicesResponse>("/api/compose/services", { content }),
  appdataPaths: (content: string) =>
    post<{ compose_text: string }>("/api/compose/appdata-paths", { content }),
  loadFromGithub: (repo_url: string) =>
    post<LoadComposeResponse>("/api/github/load-compose", { repo_url }),
  githubImages: (repo_url: string) =>
    post<{ images: string[]; message: string }>("/api/github/images", { repo_url }),
  iconPreview: (url: string) =>
    post<{ valid: boolean; message: string }>("/api/icon/preview", { url }),
  generate: (payload: { compose_content: string; services: ServiceGenerateConfig[] }) =>
    post<GenerateResponse>("/api/template/generate", payload),
  saveLocal: (items: SaveItem[]) =>
    post<{ success: boolean; saved: { filename: string; path: string }[]; message: string }>(
      "/api/template/save-local",
      { items }
    ),
  downloadZip: async (items: SaveItem[]): Promise<Blob> => {
    const res = await fetch("/api/template/download-zip", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    });
    if (!res.ok) throw new Error(`Error ${res.status} al generar el ZIP`);
    return res.blob();
  },
};
