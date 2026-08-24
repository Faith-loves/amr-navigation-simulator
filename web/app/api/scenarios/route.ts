import { scenarios } from "../../../lib/server/simulator";

export function GET() {
  return Response.json({ scenarios });
}
