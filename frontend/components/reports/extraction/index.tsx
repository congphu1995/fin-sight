import type { ReportExtraction, ReportTypeCode } from "@/lib/types";
import { CompanyExtractionView } from "./company";
import { IndustryExtractionView } from "./industry";
import { MacroExtractionView } from "./macro";
import { TechnicalExtractionView } from "./technical";
import { ThematicExtractionView } from "./thematic";
import { GenericExtractionView } from "./generic";

interface Props {
  typeCode: string;
  ext: ReportExtraction;
}

export function ExtractionView({ typeCode, ext }: Props) {
  const code = typeCode as ReportTypeCode;
  switch (code) {
    case "company":
      return <CompanyExtractionView ext={ext} />;
    case "industry":
      return <IndustryExtractionView ext={ext} />;
    case "macro":
      return <MacroExtractionView ext={ext} />;
    case "technical":
      return <TechnicalExtractionView ext={ext} />;
    case "thematic":
      return <ThematicExtractionView ext={ext} />;
    default:
      return <GenericExtractionView ext={ext} />;
  }
}
