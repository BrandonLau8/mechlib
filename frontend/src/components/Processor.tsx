import { useAuth } from '@/contexts/AuthContext'
import {Field, FieldGroup, FieldLabel, FieldSet} from "@/components/ui/field.tsx";
import {Input} from "@/components/ui/input.tsx";
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from "@/components/ui/card.tsx";
import {Button} from "@/components/ui/button.tsx";
import {MaterialsCheckBox} from "@/components/MaterialsCheckBox.tsx";
import {ProcessCheckBox} from "@/components/ProcessCheckBox.tsx";
import {useState} from "react";
import {CheckCircle2Icon} from "lucide-react";
import {Textarea} from "@/components/ui/textarea.tsx";

interface ProcessorProps {
    files: File[]
    onSuccess?: () => void
    description: string
    setDescription: (value: string) => void
    brand: string
    setBrand: (value: string) => void
    materials: string[]
    setMaterials: (value: string[]) => void
    process: string[]
    setProcess: (value: string[]) => void
    mechanism: string
    setMechanism: (value: string) => void
    project: string
    setProject: (value: string) => void
    person: string
    setPerson: (value: string) => void
    onFormClear: () => void
}

export function Processor({
    files,
    onSuccess,
    description,
    setDescription,
    brand,
    setBrand,
    materials,
    setMaterials,
    process,
    setProcess,
    mechanism,
    setMechanism,
    project,
    setProject,
    person,
    setPerson,
    onFormClear
}: ProcessorProps) {
    const { getAuthHeaders } = useAuth()
    const [isProcessing, setIsProcessing] = useState(false)
    const [processingFiles, setProcessingFiles] = useState<Set<number>>(new Set())
    const [successMessage, setSuccessMessage] = useState<string | null>(null)
    const [errorMessage, setErrorMessage] = useState<string | null>(null)
    const [abortController, setAbortController] = useState<AbortController | null>(null)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (files.length === 0) {
            console.log('Setting error: No files selected')
            setErrorMessage("Please select files first in the Upload tab")
            return
        }

        if (!description.trim() || !person.trim()) {
            console.log('Setting error: Missing required fields')
            setErrorMessage("Description and Person are required fields")
            return
        }

        // Clear any previous messages
        setSuccessMessage(null)
        setErrorMessage(null)

        // Create abort controller for cancellation
        const controller = new AbortController()
        setAbortController(controller)
        setIsProcessing(true)

        try {
            // Step 1: Upload files to backend
            const formData = new FormData()
            files.forEach(file => {
                formData.append('files', file)
            })

            console.log('=== UPLOAD REQUEST ===')
            console.log('Files to upload:', files.map(f => ({ name: f.name, size: f.size, type: f.type })))

            const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
            console.log('API URL:', `${apiUrl}/upload`)

            const uploadResponse = await fetch(`${apiUrl}/upload`, {
                method: 'POST',
                body: formData,
                headers: {
                    ...getAuthHeaders(),
                },
                signal: controller.signal,

            })

            if (!uploadResponse.ok) {
                throw new Error(`Upload failed: ${uploadResponse.statusText}`)
            }

            const uploadData = await uploadResponse.json()
            console.log('✅ Upload successful:', uploadData)

            // Step 2: Process files with metadata
            const processPayload = {
                paths: uploadData.file_paths,
                description,
                brand,
                materials,
                process,
                mechanism,
                project,
                person,
            }

            console.log('=== PROCESS REQUEST ===')
            console.log('Payload:', JSON.stringify(processPayload, null, 2))

            const processResponse = await fetch(`${apiUrl}/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders(),
                },
                body: JSON.stringify(processPayload),
                signal: controller.signal,
            })

            if (!processResponse.ok) {
                throw new Error(`Process failed: ${processResponse.statusText}`)
            }

            const processData = await processResponse.json()
            console.log('✅ Process successful:', processData)
            console.log('S3 URIs:', processData.s3_uris)

            const msg = `Successfully processed ${processData.files_processed} file(s)! Images uploaded to S3 and metadata embedded.`
            console.log('Setting success message:', msg)
            setSuccessMessage(msg)

            // Clear form
            onFormClear()

            // Files will be cleared when user closes the success alert

        } catch (error) {
            // Don't show error if user cancelled
            if (error instanceof Error && error.name === 'AbortError') {
                console.log('Processing cancelled by user')
            } else {
                console.error('Error processing files:', error)
                const msg = `Processing failed: ${error instanceof Error ? error.message : 'Unknown error'}`
                console.log('Setting error message:', msg)
                setErrorMessage(msg)
            }
        } finally {
            setIsProcessing(false)
            setProcessingFiles(new Set())
            setAbortController(null)
        }
    }

    const handleCancel = () => {
        if (abortController) {
            abortController.abort()
        }
        setIsProcessing(false)
        setProcessingFiles(new Set())
        setAbortController(null)
    }

    return (
        <div className="space-y-4">
            {/* Success Modal Overlay */}
            {successMessage && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-card border rounded-lg p-6 max-w-md w-full mx-4 shadow-lg">
                        <div className="flex flex-col items-center text-center space-y-4">
                            <CheckCircle2Icon className="size-12 text-green-600" />
                            <div>
                                <h3 className="font-semibold text-lg mb-2">Success</h3>
                                <p className="text-muted-foreground">{successMessage}</p>
                            </div>
                            <Button
                                onClick={() => {
                                    setSuccessMessage(null)
                                    if (onSuccess) {
                                        onSuccess()
                                    }
                                }}
                                className="w-full"
                            >
                                Close
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Error Modal Overlay */}
            {errorMessage && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-card border border-destructive rounded-lg p-6 max-w-md w-full mx-4 shadow-lg">
                        <div className="flex flex-col items-center text-center space-y-4">
                            <div className="size-12 rounded-full bg-destructive/10 flex items-center justify-center">
                                <span className="text-destructive text-2xl font-bold">!</span>
                            </div>
                            <div>
                                <h3 className="font-semibold text-lg mb-2 text-destructive">Error</h3>
                                <p className="text-muted-foreground">{errorMessage}</p>
                            </div>
                            <Button
                                onClick={() => setErrorMessage(null)}
                                variant="destructive"
                                className="w-full"
                            >
                                Close
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            {/* Processing Modal Overlay */}
            {isProcessing && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-card border rounded-lg p-6 max-w-md w-full mx-4 shadow-lg">
                        <div className="flex flex-col items-center text-center space-y-4">
                            <div className="text-primary">
                                <svg className="animate-spin size-12" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            </div>
                            <div>
                                <h3 className="font-semibold text-lg mb-2">Processing Images</h3>
                                <p className="text-muted-foreground">
                                    Processing {files.length} file(s)...
                                    <br />
                                    Please wait while we upload and embed metadata.
                                </p>
                            </div>
                            <Button
                                onClick={handleCancel}
                                variant="outline"
                                className="w-full"
                            >
                                Cancel
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            <Card className="">
                <CardHeader>
                    <CardTitle>Process Images</CardTitle>
                    <CardDescription>
                        {files.length > 0
                            ? `${files.length} file(s) selected`
                            : "No files selected. Go to Upload tab to select files."}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit}>
                        <FieldSet>
                            <FieldGroup>
                                <Field>
                                    <FieldLabel htmlFor="description">Description *</FieldLabel>
                                    <Textarea
                                        id="description"
                                        placeholder="Describe the image and/or add a link"
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                        required
                                        disabled={isProcessing}
                                    />
                                </Field>

                                <Field>
                                    <FieldLabel htmlFor="brand">Brand</FieldLabel>
                                    <Input
                                        id="brand"
                                        type="text"
                                        placeholder="Name of the product brand"
                                        value={brand}
                                        onChange={(e) => setBrand(e.target.value)}
                                        disabled={isProcessing}
                                    />
                                </Field>

                                <MaterialsCheckBox
                                    value={materials}
                                    onChange={setMaterials}
                                    disabled={isProcessing}
                                />

                                <ProcessCheckBox
                                    value={process}
                                    onChange={setProcess}
                                    disabled={isProcessing}
                                />

                                <Field>
                                    <FieldLabel htmlFor="mechanism">Mechanism</FieldLabel>
                                    <Input
                                        id="mechanism"
                                        type="text"
                                        placeholder="ex. Linear switch, Bayonet, etc..."
                                        value={mechanism}
                                        onChange={(e) => setMechanism(e.target.value)}
                                        disabled={isProcessing}
                                    />
                                </Field>

                                <Field>
                                    <FieldLabel htmlFor="project">Project</FieldLabel>
                                    <Input
                                        id="project"
                                        type="text"
                                        placeholder="Name of the project"
                                        value={project}
                                        onChange={(e) => setProject(e.target.value)}
                                        disabled={isProcessing}
                                    />
                                </Field>

                                <Field>
                                    <FieldLabel htmlFor="person">Person *</FieldLabel>
                                    <Input
                                        id="person"
                                        type="text"
                                        placeholder="Your initials"
                                        value={person}
                                        onChange={(e) => setPerson(e.target.value)}
                                        required
                                        disabled={isProcessing}
                                    />
                                </Field>

                                <Field orientation="horizontal">
                                    <Button
                                        type="submit"
                                        disabled={isProcessing || files.length === 0 || !description.trim() || !person.trim()}
                                    >
                                        {isProcessing ? 'Processing...' : 'Process Images'}
                                    </Button>
                                    {/*<Button variant="outline" type="button" disabled={isProcessing}>*/}
                                    {/*    Cancel*/}
                                    {/*</Button>*/}
                                </Field>
                            </FieldGroup>
                        </FieldSet>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}

