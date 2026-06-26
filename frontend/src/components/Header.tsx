import { ThemeToggle } from "@/components/ThemeToggle";

export function Header() {
  return (
    <header className="relative flex flex-col items-center pt-10 pb-4">
      {/* Logo y toggle anclados a los extremos del viewport (no al contenedor) */}
      <img
        src="/unposer-logo-trans.png"
        alt="UNPOSER"
        className="fixed left-6 top-5 h-20 w-20"
      />
      <div className="fixed right-6 top-6">
        <ThemeToggle />
      </div>
      <h1 className="text-4xl font-bold tracking-tight">UNPOSER</h1>
      <p className="mt-2 text-lg text-muted-foreground">
        Convierte Docker Compose a Plantilla Unraid
      </p>
    </header>
  );
}
