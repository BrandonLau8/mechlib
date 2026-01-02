

import './App.css'
import { ImageUploader } from "./components/ImageUploader"
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs.tsx";
import {Processor} from "@/components/Processor.tsx";
import { useState } from "react"
import {ThemeProvider} from "@/components/theme-provider.tsx";
import {SearchComponent} from "@/components/SearchComponent.tsx";
import { type GalleryImage } from "@/components/Gallery.tsx";
import {GoogleOAuthProvider} from "@react-oauth/google";
import AuthProvider, {useAuth} from "@/contexts/AuthContext.tsx";
import {Login} from "@/components/Login.tsx";
import { Button } from "./components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "./components/ui/avatar";
import { LogOut } from "lucide-react";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

// Separate component that uses useAuth (must be inside AuthProvider)
function AppContent() {
    const { isAuthenticated, user, logout } = useAuth()

    const [files, setFiles] = useState<File[]>([])
    const [activeTab, setActiveTab] = useState("upload")

  // Form state - persists across tab switches
  const [description, setDescription] = useState("")
  const [brand, setBrand] = useState("")
  const [materials, setMaterials] = useState<string[]>([])
  const [process, setProcess] = useState<string[]>([])
  const [mechanism, setMechanism] = useState("")
  const [project, setProject] = useState("")
  const [person, setPerson] = useState("")

  // Search state - persists across tab switches
  const [searchQuery, setSearchQuery] = useState("")
  const [searchK, setSearchK] = useState(10)
  const [searchScoreThreshold, setSearchScoreThreshold] = useState(1.0)
  const [searchResults, setSearchResults] = useState<GalleryImage[]>([])
  const [searchMessage, setSearchMessage] = useState<string | null>(null)
  const [searchTotalCount, setSearchTotalCount] = useState(0)
  const [searchFilteredCount, setSearchFilteredCount] = useState(0)

  const clearFiles = () => {
    setFiles([])
    setActiveTab("upload")  // Switch back to upload tab
  }

  const clearForm = () => {
    setDescription("")
    setBrand("")
    setMaterials([])
    setProcess([])
    setMechanism("")
    setProject("")
    setPerson("")
  }

    // Show login page if not authenticated
    if (!isAuthenticated) {
        return <Login />
    }

    return (
        <div>
            {/* User info header */}
            <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
                <div className="container flex h-16 items-center justify-between px-6">
                    <div className="flex items-center gap-4">
                        <h1 className="text-xl font-semibold tracking-tight">MechLib</h1>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className="flex items-center gap-3">
                            <Avatar className="h-9 w-9 ring-2 ring-border">
                                <AvatarImage src={user?.picture} alt={user?.name} />
                                <AvatarFallback className="bg-primary/10 text-primary font-medium">
                                    {user?.name?.charAt(0).toUpperCase()}
                                </AvatarFallback>
                            </Avatar>
                            <div className="hidden sm:block">
                                <div className="text-sm font-medium leading-none">{user?.name}</div>
                                <div className="text-xs text-muted-foreground mt-1">{user?.email}</div>
                            </div>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={logout}
                            className="gap-2"
                        >
                            <LogOut className="h-4 w-4" />
                            Sign Out
                        </Button>
                    </div>
                </div>
            </header>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="container px-6 pt-6">
                <TabsList>
                    <TabsTrigger value="upload">Upload</TabsTrigger>
                    <TabsTrigger value="process">Process ({files.length})</TabsTrigger>
                    <TabsTrigger value="search">Search</TabsTrigger>
                </TabsList>
                <TabsContent value="upload">
                    <ImageUploader files={files} setFiles={setFiles} />
                </TabsContent>
                <TabsContent value="process">
                    <Processor
                        files={files}
                        onSuccess={clearFiles}
                        description={description}
                        setDescription={setDescription}
                        brand={brand}
                        setBrand={setBrand}
                        materials={materials}
                        setMaterials={setMaterials}
                        process={process}
                        setProcess={setProcess}
                        mechanism={mechanism}
                        setMechanism={setMechanism}
                        project={project}
                        setProject={setProject}
                        person={person}
                        setPerson={setPerson}
                        onFormClear={clearForm}
                    />
                </TabsContent>
                <TabsContent value="search">
                    <SearchComponent
                        query={searchQuery}
                        setQuery={setSearchQuery}
                        k={searchK}
                        setK={setSearchK}
                        scoreThreshold={searchScoreThreshold}
                        setScoreThreshold={setSearchScoreThreshold}
                        results={searchResults}
                        setResults={setSearchResults}
                        searchMessage={searchMessage}
                        setSearchMessage={setSearchMessage}
                        totalCount={searchTotalCount}
                        setTotalCount={setSearchTotalCount}
                        filteredCount={searchFilteredCount}
                        setFilteredCount={setSearchFilteredCount}
                    />
                </TabsContent>
            </Tabs>
        </div>
    )
}

// Main App component - providers wrap everything
function App() {
    return (
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <AuthProvider>
                <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
                    <AppContent />
                </ThemeProvider>
            </AuthProvider>
        </GoogleOAuthProvider>
    )
}

export default App
