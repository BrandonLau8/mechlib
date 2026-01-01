

import './App.css'
import { ImageUploader } from "./components/ImageUploader"
import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs.tsx";
import {Processor} from "@/components/Processor.tsx";
import { useState } from "react"
import {ThemeProvider} from "@/components/theme-provider.tsx";
import {SearchComponent} from "@/components/SearchComponent.tsx";
import { type GalleryImage } from "@/components/Gallery.tsx";

function App() {
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
  const [searchScoreThreshold, setSearchScoreThreshold] = useState(0.5)
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

  return (
      <ThemeProvider defaultTheme="dark" storageKey="vite-ui-theme">
    <div>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="">
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
      </ThemeProvider>
  )
}

export default App
