import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { ResearchView } from "@/components/research/research-view";
import { SiteHeader } from "@/components/site-header";
import { MOCK_QUESTION } from "@/lib/mock-stream";
import type { Mode } from "@/lib/types";

const MAX_QUESTION = 500;

type Search = { q?: string; mode?: string; demo?: string };

function parse(sp: Search) {
  const demo = sp.demo === "1";
  // The demo replays a scripted run, so it always shows the scripted question.
  const question = demo ? MOCK_QUESTION : (sp.q ?? "").trim().slice(0, MAX_QUESTION);
  const mode: Mode = sp.mode === "lenient" ? "lenient" : "strict";
  return { question, mode, demo };
}

export async function generateMetadata(props: PageProps<"/research">): Promise<Metadata> {
  const { question } = parse(await props.searchParams);
  return { title: question || "Research" };
}

export default async function ResearchPage(props: PageProps<"/research">) {
  const { question, mode, demo } = parse(await props.searchParams);
  if (question.length < 3) redirect("/");
  return (
    <>
      <SiteHeader />
      {/* key: a new question remounts the view and starts a fresh run */}
      <ResearchView key={`${question}|${mode}|${demo}`} question={question} mode={mode} demo={demo} />
    </>
  );
}
