import { beforeEach, describe, expect, it, vi, type Mock } from "vitest";

vi.mock("@/infrastructure/api/httpClient", () => ({
  httpClient: { get: vi.fn(), post: vi.fn(), postWithResponse: vi.fn(), delete: vi.fn() },
}));

import {
  linkMatterProperty,
  listMatterProperties,
  unlinkMatterProperty,
} from "@/infrastructure/api/mattersApi";
import { httpClient } from "@/infrastructure/api/httpClient";

const mockedGet = httpClient.get as unknown as Mock;
const mockedPostWithResponse = httpClient.postWithResponse as unknown as Mock;
const mockedDelete = httpClient.delete as unknown as Mock;
const PATH = "/api/v1/matters/m1/properties";
const PROPERTY = { id: "p1", survey_number: "42" };

describe("MatterProperty API adapters", () => {
  beforeEach(() => {
    mockedGet.mockReset();
    mockedPostWithResponse.mockReset();
    mockedDelete.mockReset();
  });

  it("unwraps the canonical Matter-scoped association list", async () => {
    mockedGet.mockResolvedValue({ data: [PROPERTY] });

    await expect(listMatterProperties("m1")).resolves.toEqual([PROPERTY]);
    expect(mockedGet).toHaveBeenCalledWith(PATH);
  });

  it("posts the existing Property id and recognizes a newly created association", async () => {
    mockedPostWithResponse.mockResolvedValue({ data: { data: PROPERTY }, status: 201 });

    await expect(linkMatterProperty("m1", "p1")).resolves.toEqual({
      property: PROPERTY,
      created: true,
    });
    expect(mockedPostWithResponse).toHaveBeenCalledWith(PATH, { property_id: "p1" });
  });

  it("preserves the documented 200 duplicate response as an idempotent result", async () => {
    mockedPostWithResponse.mockResolvedValue({ data: { data: PROPERTY }, status: 200 });

    await expect(linkMatterProperty("m1", "p1")).resolves.toEqual({
      property: PROPERTY,
      created: false,
    });
  });

  it("uses the canonical unlink endpoint without a Property deletion request", async () => {
    mockedDelete.mockResolvedValue(undefined);

    await expect(unlinkMatterProperty("m1", "p1")).resolves.toBeUndefined();
    expect(mockedDelete).toHaveBeenCalledWith(`${PATH}/p1`);
  });
});
