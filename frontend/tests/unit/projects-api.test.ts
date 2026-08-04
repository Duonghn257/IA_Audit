import { afterEach, describe, expect, it, vi } from "vitest"

import { uploadProject } from "../../src/shared/api/projects"

describe("project upload", () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("replaces a root sample_issues.json with the reviewed form input", async () => {
    let submittedForm: FormData | null = null

    class MockXmlHttpRequest {
      readonly upload = new EventTarget()
      status = 202
      responseText = JSON.stringify({ project_id: "project-1" })
      private readonly listeners = new Map<string, EventListener>()

      open(): void {}
      setRequestHeader(): void {}
      addEventListener(type: string, listener: EventListener): void {
        this.listeners.set(type, listener)
      }
      send(body: Document | XMLHttpRequestBodyInit | null): void {
        submittedForm = body as FormData
        this.listeners.get("load")?.(new Event("load"))
      }
    }

    vi.stubGlobal("XMLHttpRequest", MockXmlHttpRequest)

    const evidence = folderFile(
      "access-review.docx",
      "Ariba Audit/Process Understanding/access-review.docx",
      "evidence",
    )
    const oldJson = folderFile(
      "sample_issues.json",
      "Ariba Audit/sample_issues.json",
      "[]",
    )

    await uploadProject(
      {
        name: "Ariba Audit",
        files: [evidence, oldJson],
        auditorIssues: [
          {
            title_hint: "Strengthen access segregation",
            observed_gap: "Two profiles have the same access.",
            evidence_summary: "The access matrix was reviewed.",
            evidence_refs: ["Process Understanding/access-review.docx"],
            sop_refs: [],
            risk_category: "IT",
          },
        ],
      },
      () => undefined,
    )

    expect(submittedForm).not.toBeNull()
    const form = submittedForm as unknown as FormData
    const paths = form.getAll("relative_paths")
    expect(paths).toEqual([
      "Ariba Audit/Process Understanding/access-review.docx",
      "Ariba Audit/sample_issues.json",
    ])

    const uploadedFiles = form.getAll("files") as File[]
    expect(uploadedFiles.map((file) => file.name)).toEqual([
      "access-review.docx",
      "sample_issues.json",
    ])

    const generatedJson = uploadedFiles.find((file) => file.name === "sample_issues.json")
    expect(generatedJson).toBeDefined()
    const generatedText = await readFile(generatedJson!)
    expect(JSON.parse(generatedText)[0].observed_gap).toBe(
      "Two profiles have the same access.",
    )
  })
})

function folderFile(name: string, relativePath: string, content: string): File {
  const file = new File([content], name)
  Object.defineProperty(file, "webkitRelativePath", { value: relativePath })
  return file
}

function readFile(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.addEventListener("load", () => resolve(String(reader.result || "")))
    reader.addEventListener("error", () => reject(reader.error))
    reader.readAsText(file)
  })
}
