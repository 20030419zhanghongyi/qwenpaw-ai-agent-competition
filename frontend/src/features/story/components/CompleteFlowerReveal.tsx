import type { CSSProperties } from "react";
import { StoryImage } from "../assets";

const PETAL_ASSET_IDS = [
  "V4-AMA-05",
  "V4-MAN-06",
  "V4-SEN-05",
  "V4-SAM-06",
  "V4-LOU-05",
];

const PETAL_ROTATIONS = [-72, -36, 0, 36, 72];

export function CompleteFlowerReveal() {
  return (
    <div>
      <div
        className="story-flower-reveal relative mx-auto aspect-[4/5] w-44"
        role="img"
        aria-label="五张密笺花瓣依次重合，组成完整澳门市花"
      >
        <div className="story-flower-petal-group absolute inset-0" aria-hidden>
          {PETAL_ASSET_IDS.map((assetId, index) => (
            <div
              key={assetId}
              className="story-flower-petal absolute left-1/2 top-[43%] w-[46%]"
              style={
                {
                  "--petal-index": index,
                  "--petal-rotation": `${PETAL_ROTATIONS[index]}deg`,
                } as CSSProperties
              }
            >
              <StoryImage
                assetId={assetId}
                alt=""
                eager
                className="rounded-none border-0 bg-transparent"
                imageClassName="object-contain"
              />
            </div>
          ))}
        </div>
        <div className="story-flower-final absolute inset-0">
          <StoryImage
            assetId="V4-LOU-06"
            alt=""
            eager
            className="size-full border-0 bg-transparent"
            imageClassName="object-contain"
          />
        </div>
      </div>
      <p className="mt-2 text-sm leading-6 text-sage-deep">
        五瓣已经集齐，五张密笺迎光组成完整市花。
      </p>
    </div>
  );
}
