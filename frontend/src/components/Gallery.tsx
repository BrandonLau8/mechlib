import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { ChevronDown, ChevronUp, Pencil, Trash2 } from "lucide-react"
import { useState } from "react"

export interface GalleryImage {
  url: string
  filename: string
  description?: string
  brand?: string
  materials?: string[]
  process?: string[]
  mechanism?: string
  project?: string
  person?: string
  timestamp?: string
  s3_uri?: string
}

interface GalleryProps {
  images: GalleryImage[]
  className?: string
  onUpdate?: (image: GalleryImage) => void
  onDelete?: (image: GalleryImage) => void
}

function linkifyText(text: string): React.ReactNode {
  if (!text) return text

  // Regex pattern for URLs (http, https)
  const urlPattern = /(https?:\/\/[^\s<>"]+)/g
  const parts = text.split(urlPattern)

  return parts.map((part, index) => {
    if (part.match(urlPattern)) {
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-500 hover:text-blue-700 underline"
          onClick={(e) => e.stopPropagation()}
        >
          {part}
        </a>
      )
    }
    return part
  })
}

interface GalleryItemProps {
  image: GalleryImage
  onEdit?: (image: GalleryImage) => void
  onDelete?: (image: GalleryImage) => void
}

function GalleryItem({ image, onEdit, onDelete }: GalleryItemProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isTruncated, setIsTruncated] = useState(false)

  const handleDescriptionRef = (element: HTMLParagraphElement | null) => {
    if (element && !isExpanded) {
      setIsTruncated(element.scrollHeight > element.clientHeight)
    }
  }

  return (
    <Card className="overflow-hidden transition-transform hover:-translate-y-1 hover:shadow-lg group">
      <CardContent className="p-0">
        <div className="relative">
          <img
            src={image.url}
            alt={image.filename}
            className="w-full h-auto block object-cover"
            loading="lazy"
          />
          {/* Action buttons - show on hover */}
          {(onEdit || onDelete) && (
            <div className="absolute top-2 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              {onEdit && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onEdit(image)}
                  className="h-8 w-8 p-0 shadow-lg"
                >
                  <Pencil className="size-4" />
                </Button>
              )}
              {onDelete && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => onDelete(image)}
                  className="h-8 w-8 p-0 shadow-lg"
                >
                  <Trash2 className="size-4" />
                </Button>
              )}
            </div>
          )}
        </div>
        <div className="p-3 space-y-2">
          <p
            ref={handleDescriptionRef}
            className={cn(
              "text-sm text-muted-foreground text-center leading-relaxed",
              !isExpanded && "line-clamp-3"
            )}
            title={image.description}
          >
            {linkifyText(image.description || "")}
          </p>
          {isTruncated && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="w-full h-auto py-1 text-xs font-normal"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="size-3 mr-1" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="size-3 mr-1" />
                  Read more
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export function Gallery({ images, className, onUpdate, onDelete }: GalleryProps) {
  if (!images || images.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-12">
        <p className="text-lg">No images found</p>
        <p className="text-sm mt-2">Try adjusting your search query or threshold</p>
      </div>
    )
  }

  return (
    <div className={cn("w-full", className)}>
      <h2 className="text-2xl font-semibold text-center mb-6">
        Image Gallery
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {images.map((image, index) => (
          <GalleryItem
            key={`${image.filename}-${index}`}
            image={image}
            onEdit={onUpdate}
            onDelete={onDelete}
          />
        ))}
      </div>
    </div>
  )
}
