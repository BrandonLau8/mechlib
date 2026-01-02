import { useAuth } from '@/contexts/AuthContext'
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group.tsx"
import { Search, Loader2, X } from "lucide-react"
import { useState } from "react"
import { Gallery, type GalleryImage } from "./Gallery"
import { Button } from "@/components/ui/button"
import { Field, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { MaterialsCheckBox } from "./MaterialsCheckBox"
import { ProcessCheckBox } from "./ProcessCheckBox"

interface SearchResponse {
    query: string
    results: Array<{
        url: string
        s3_uri: string
        filename: string
        description?: string
        brand?: string
        materials?: string[]
        process?: string[]
        mechanism?: string
        project?: string
        person?: string
        timestamp?: string
        score: number
    }>
    total_count: number
    filtered_count: number
    message?: string
}

interface SearchComponentProps {
    query: string
    setQuery: (query: string) => void
    k: number
    setK: (k: number) => void
    scoreThreshold: number
    setScoreThreshold: (threshold: number) => void
    results: GalleryImage[]
    setResults: (results: GalleryImage[]) => void
    searchMessage: string | null
    setSearchMessage: (message: string | null) => void
    totalCount: number
    setTotalCount: (count: number) => void
    filteredCount: number
    setFilteredCount: (count: number) => void
}

export function SearchComponent({
    query,
    setQuery,
    k,
    setK,
    scoreThreshold,
    setScoreThreshold,
    results,
    setResults,
    searchMessage,
    setSearchMessage,
    totalCount,
    setTotalCount,
    filteredCount,
    setFilteredCount
}: SearchComponentProps) {
    const {getAuthHeaders} = useAuth()
    const [isSearching, setIsSearching] = useState(false)

    // Edit/Delete state
    const [editImage, setEditImage] = useState<GalleryImage | null>(null)
    const [deleteImage, setDeleteImage] = useState<GalleryImage | null>(null)
    const [isUpdating, setIsUpdating] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)

    const handleUpdate = async (updatedImage: GalleryImage) => {
        if (!updatedImage.s3_uri) return

        setIsUpdating(true)
        try {
            const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
            const response = await fetch(`${apiUrl}/update-metadata`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify({
                    s3_uri: updatedImage.s3_uri,
                    description: updatedImage.description,
                    brand: updatedImage.brand,
                    materials: updatedImage.materials,
                    process: updatedImage.process,
                    mechanism: updatedImage.mechanism,
                    project: updatedImage.project,
                    person: updatedImage.person,
                }),
            })

            if (!response.ok) {
                throw new Error(`Update failed: ${response.statusText}`)
            }

            // Update local state
            setResults(results.map(img =>
                img.s3_uri === updatedImage.s3_uri ? updatedImage : img
            ))
            setEditImage(null)
            setSearchMessage("Image metadata updated successfully")
        } catch (error) {
            console.error('Update error:', error)
            setSearchMessage(`Update failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
        } finally {
            setIsUpdating(false)
        }
    }

    const handleDelete = async (imageToDelete: GalleryImage) => {
        if (!imageToDelete.s3_uri) return

        setIsDeleting(true)
        try {
            const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
            const response = await fetch(`${apiUrl}/delete-image`, {
                method: 'DELETE',
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    s3_uri: imageToDelete.s3_uri,
                    filename: imageToDelete.filename,
                }),
            })

            if (!response.ok) {
                throw new Error(`Delete failed: ${response.statusText}`)
            }

            // Remove from local state
            setResults(results.filter(img => img.s3_uri !== imageToDelete.s3_uri))
            setFilteredCount(filteredCount - 1)
            setDeleteImage(null)
            setSearchMessage("Image deleted successfully")
        } catch (error) {
            console.error('Delete error:', error)
            setSearchMessage(`Delete failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
        } finally {
            setIsDeleting(false)
        }
    }

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!query.trim()) {
            setSearchMessage("Please enter a search query")
            return
        }

        setIsSearching(true)
        setSearchMessage(null)

        try {
            const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
            const response = await fetch(`${apiUrl}/search`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify({
                    query: query.trim(),
                    k,
                    score_threshold: scoreThreshold,
                }),
            })

            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`)
            }

            const data: SearchResponse = await response.json()

            // Convert search results to GalleryImage format
            const galleryImages: GalleryImage[] = data.results.map(result => ({
                url: result.url,
                filename: result.filename,
                description: result.description,
                brand: result.brand,
                materials: result.materials,
                process: result.process,
                mechanism: result.mechanism,
                project: result.project,
                person: result.person,
                timestamp: result.timestamp,
                s3_uri: result.s3_uri,
            }))

            setResults(galleryImages)
            setTotalCount(data.total_count)
            setFilteredCount(data.filtered_count)

            if (data.message) {
                setSearchMessage(data.message)
            } else if (data.filtered_count > 0) {
                setSearchMessage(`Found ${data.filtered_count} image(s) matching your query`)
            }
        } catch (error) {
            console.error('Search error:', error)
            setSearchMessage(`Search failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
            setResults([])
        } finally {
            setIsSearching(false)
        }
    }

    return (
        <div className="space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>Search Images</CardTitle>
                    <CardDescription>
                        Search for images using semantic search
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSearch} className="space-y-4">
                        <Field>
                            <FieldLabel htmlFor="query">Search Query</FieldLabel>
                            <InputGroup>
                                <InputGroupInput
                                    id="query"
                                    placeholder="e.g., mechanical keyboard switch, aluminum fastener..."
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value)}
                                    disabled={isSearching}
                                />
                                <InputGroupAddon>
                                    {isSearching ? (
                                        <Loader2 className="animate-spin" />
                                    ) : (
                                        <Search />
                                    )}
                                </InputGroupAddon>
                            </InputGroup>
                        </Field>

                        <div className="grid grid-cols-2 gap-4">
                            <Field>
                                <FieldLabel htmlFor="k">Results (max)</FieldLabel>
                                <Input
                                    id="k"
                                    type="number"
                                    min={1}
                                    max={50}
                                    value={k}
                                    onChange={(e) => setK(Number(e.target.value))}
                                    disabled={isSearching}
                                />
                            </Field>

                            <Field>
                                <FieldLabel htmlFor="threshold">
                                    Score Threshold
                                    <span className="text-xs text-muted-foreground ml-1">(0.3-1.0)</span>
                                </FieldLabel>
                                <Input
                                    id="threshold"
                                    type="number"
                                    step={0.1}
                                    min={0}
                                    max={2}
                                    value={scoreThreshold}
                                    onChange={(e) => setScoreThreshold(Number(e.target.value))}
                                    disabled={isSearching}
                                />
                            </Field>
                        </div>

                        <div className="text-xs text-muted-foreground space-y-1">
                            <p><strong>Threshold Guide:</strong></p>
                            <ul className="list-disc list-inside ml-2 space-y-0.5">
                                <li>0.3-0.4: Only nearly identical matches</li>
                                <li>0.5: Very relevant results (recommended)</li>
                                <li>0.6-0.7: Relevant with flexibility</li>
                                <li>0.8+: Includes loosely related images</li>
                            </ul>
                        </div>

                        <Button type="submit" disabled={isSearching || !query.trim()} className="w-full">
                            {isSearching ? 'Searching...' : 'Search'}
                        </Button>
                    </form>

                    {searchMessage && (
                        <div className="mt-4 p-3 rounded-md bg-muted text-sm text-center">
                            {searchMessage}
                        </div>
                    )}

                    {!isSearching && filteredCount > 0 && (
                        <div className="mt-4 text-sm text-muted-foreground text-center">
                            Showing {filteredCount} of {totalCount} results
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Edit Image Dialog */}
            {editImage && (
                <EditImageDialog
                    image={editImage}
                    isUpdating={isUpdating}
                    onSave={(updatedImage) => handleUpdate(updatedImage)}
                    onClose={() => setEditImage(null)}
                />
            )}

            {/* Delete Confirmation Dialog */}
            {deleteImage && (
                <DeleteConfirmDialog
                    image={deleteImage}
                    isDeleting={isDeleting}
                    onConfirm={() => handleDelete(deleteImage)}
                    onCancel={() => setDeleteImage(null)}
                />
            )}

            {/* Gallery Results */}
            {results.length > 0 && (
                <Gallery
                    images={results}
                    className="mt-8"
                    onUpdate={setEditImage}
                    onDelete={setDeleteImage}
                />
            )}
        </div>
    )
}

// Edit Image Dialog Component
function EditImageDialog({
    image,
    isUpdating,
    onSave,
    onClose
}: {
    image: GalleryImage
    isUpdating: boolean
    onSave: (image: GalleryImage) => void
    onClose: () => void
}) {
    const [description, setDescription] = useState(image.description || "")
    const [brand, setBrand] = useState(image.brand || "")
    const [materials, setMaterials] = useState<string[]>(image.materials || [])
    const [process, setProcess] = useState<string[]>(image.process || [])
    const [mechanism, setMechanism] = useState(image.mechanism || "")
    const [project, setProject] = useState(image.project || "")
    const [person, setPerson] = useState(image.person || "")

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        onSave({
            ...image,
            description,
            brand,
            materials,
            process,
            mechanism,
            project,
            person,
        })
    }

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-card border rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-lg custom-scrollbar">
                <div className="sticky top-0 bg-card border-b p-4 flex justify-between items-center">
                    <h3 className="font-semibold text-lg">Edit Image Metadata</h3>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onClose}
                        disabled={isUpdating}
                        className="h-8 w-8 p-0"
                    >
                        <X className="size-4" />
                    </Button>
                </div>
                <form onSubmit={handleSubmit} className="p-4 space-y-4">
                    <div className="mb-4">
                        <img
                            src={image.url}
                            alt={image.filename}
                            className="w-full max-h-64 object-contain rounded border"
                        />
                        <p className="text-sm text-muted-foreground mt-2 text-center">
                            {image.filename}
                        </p>
                    </div>

                    <Field>
                        <FieldLabel htmlFor="edit-description">Description</FieldLabel>
                        <Textarea
                            id="edit-description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            disabled={isUpdating}
                            placeholder="Describe the image..."
                        />
                    </Field>

                    <Field>
                        <FieldLabel htmlFor="edit-brand">Brand</FieldLabel>
                        <Input
                            id="edit-brand"
                            value={brand}
                            onChange={(e) => setBrand(e.target.value)}
                            disabled={isUpdating}
                            placeholder="Brand name"
                        />
                    </Field>

                    <MaterialsCheckBox
                        value={materials}
                        onChange={setMaterials}
                        disabled={isUpdating}
                    />

                    <ProcessCheckBox
                        value={process}
                        onChange={setProcess}
                        disabled={isUpdating}
                    />

                    <Field>
                        <FieldLabel htmlFor="edit-mechanism">Mechanism</FieldLabel>
                        <Input
                            id="edit-mechanism"
                            value={mechanism}
                            onChange={(e) => setMechanism(e.target.value)}
                            disabled={isUpdating}
                            placeholder="ex. Linear switch, Bayonet, etc..."
                        />
                    </Field>

                    <Field>
                        <FieldLabel htmlFor="edit-project">Project</FieldLabel>
                        <Input
                            id="edit-project"
                            value={project}
                            onChange={(e) => setProject(e.target.value)}
                            disabled={isUpdating}
                            placeholder="Project name"
                        />
                    </Field>

                    <Field>
                        <FieldLabel htmlFor="edit-person">Person</FieldLabel>
                        <Input
                            id="edit-person"
                            value={person}
                            onChange={(e) => setPerson(e.target.value)}
                            disabled={isUpdating}
                            placeholder="Your initials"
                        />
                    </Field>

                    <div className="flex gap-2 pt-4">
                        <Button
                            type="submit"
                            disabled={isUpdating}
                            className="flex-1"
                        >
                            {isUpdating ? "Saving..." : "Save Changes"}
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={onClose}
                            disabled={isUpdating}
                            className="flex-1"
                        >
                            Cancel
                        </Button>
                    </div>
                </form>
            </div>
        </div>
    )
}

// Delete Confirmation Dialog Component
function DeleteConfirmDialog({
    image,
    isDeleting,
    onConfirm,
    onCancel
}: {
    image: GalleryImage
    isDeleting: boolean
    onConfirm: () => void
    onCancel: () => void
}) {
    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-card border border-destructive rounded-lg max-w-md w-full shadow-lg">
                <div className="p-6 space-y-4">
                    <div className="flex flex-col items-center text-center space-y-3">
                        <div className="size-12 rounded-full bg-destructive/10 flex items-center justify-center">
                            <span className="text-destructive text-2xl font-bold">!</span>
                        </div>
                        <div>
                            <h3 className="font-semibold text-lg text-destructive mb-2">
                                Delete Image
                            </h3>
                            <p className="text-muted-foreground text-sm">
                                Are you sure you want to delete <strong>{image.filename}</strong>?
                            </p>
                            <p className="text-muted-foreground text-sm mt-2">
                                This will remove the image from S3 and the vector database. This action cannot be undone.
                            </p>
                        </div>
                        <img
                            src={image.url}
                            alt={image.filename}
                            className="w-full max-h-48 object-contain rounded border mt-4"
                        />
                    </div>
                    <div className="flex gap-2">
                        <Button
                            variant="destructive"
                            onClick={onConfirm}
                            disabled={isDeleting}
                            className="flex-1"
                        >
                            {isDeleting ? "Deleting..." : "Delete"}
                        </Button>
                        <Button
                            variant="outline"
                            onClick={onCancel}
                            disabled={isDeleting}
                            className="flex-1"
                        >
                            Cancel
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    )
}
