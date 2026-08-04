import { describe, expect, it } from "vitest"

import {
  AuditorInputParseError,
  createEmptyAuditorIssue,
  parseAuditorIssuesJson,
  serialiseAuditorIssues,
  sourceArtifactReference,
} from "../../src/shared/auditor-inputs"

describe("auditor input helpers", () => {
  it("creates an editable blank issue", () => {
    expect(createEmptyAuditorIssue()).toEqual({
      title_hint: "",
      observed_gap: "",
      evidence_summary: "",
      evidence_refs: [],
      sop_refs: [],
      risk_category: "",
    })
  })

  it("keeps only source artefacts supported by the backend parser", () => {
    expect(sourceArtifactReference(projectFile("Audit/APM/memo.docx"))).toBe(
      "APM/memo.docx",
    )
    expect(
      sourceArtifactReference(projectFile("Audit/Process Understanding/testing.xlsx")),
    ).toBe("Process Understanding/testing.xlsx")
    expect(sourceArtifactReference(projectFile("Audit/Process SOP/POLICY.PDF"))).toBe(
      "Process SOP/POLICY.PDF",
    )

    expect(sourceArtifactReference(projectFile("Audit/.DS_Store"))).toBeNull()
    expect(
      sourceArtifactReference(projectFile("Audit/Process Understanding/.DS_Store")),
    ).toBeNull()
    expect(sourceArtifactReference(projectFile("Audit/Output/draft.docx"))).toBeNull()
    expect(sourceArtifactReference(projectFile("Audit/Output/v0.1/draft.json"))).toBeNull()
    expect(sourceArtifactReference(projectFile("Audit/Process SOP/policy.txt"))).toBeNull()
    expect(sourceArtifactReference(projectFile("Audit/Process SOP/~$policy.docx"))).toBeNull()
    expect(
      sourceArtifactReference(projectFile("Audit/Process SOP/archive/policy.pdf")),
    ).toBeNull()
  })

  it("parses, trims and de-duplicates imported issues", () => {
    const issues = parseAuditorIssuesJson(JSON.stringify([
      {
        title_hint: "  Strengthen privileged access  ",
        observed_gap: "  Both admin profiles have the same access. ",
        evidence_summary: " Access matrix reviewed. ",
        evidence_refs: [" AWP/access.docx ", "AWP/access.docx"],
        sop_refs: ["Process SOP/security.pdf"],
        risk_category: " IT ",
      },
    ]))

    expect(issues).toEqual([
      {
        title_hint: "Strengthen privileged access",
        observed_gap: "Both admin profiles have the same access.",
        evidence_summary: "Access matrix reviewed.",
        evidence_refs: ["AWP/access.docx"],
        sop_refs: ["Process SOP/security.pdf"],
        risk_category: "IT",
      },
    ])
  })

  it("rejects malformed or incomplete JSON", () => {
    expect(() => parseAuditorIssuesJson("{")).toThrow(AuditorInputParseError)
    expect(() => parseAuditorIssuesJson("[]")).toThrow("non-empty array")
    expect(() =>
      parseAuditorIssuesJson(JSON.stringify([{ evidence_summary: "Evidence" }])),
    ).toThrow("observed_gap is required")
  })

  it("serialises the reviewed form using the pipeline contract", () => {
    const json = serialiseAuditorIssues([
      {
        title_hint: "  Access should be segregated ",
        observed_gap: " Profiles overlap ",
        evidence_summary: " Matrix reviewed ",
        evidence_refs: [" evidence.docx ", "evidence.docx"],
        sop_refs: [],
        risk_category: " IT ",
      },
    ])

    expect(JSON.parse(json)).toEqual([
      {
        title_hint: "Access should be segregated",
        observed_gap: "Profiles overlap",
        evidence_summary: "Matrix reviewed",
        evidence_refs: ["evidence.docx"],
        sop_refs: [],
        risk_category: "IT",
      },
    ])
  })
})

function projectFile(webkitRelativePath: string): Pick<File, "name" | "webkitRelativePath"> {
  return {
    name: webkitRelativePath.split("/").at(-1) || "",
    webkitRelativePath,
  }
}
