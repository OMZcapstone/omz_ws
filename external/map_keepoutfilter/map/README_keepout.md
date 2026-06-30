# OMZ Keepout Zone Package

## 포함 파일

- `omz_map.pgm` : 원본 지도
- `omz_map.png` : 원본 지도를 PNG로 변환한 파일
- `omz_map.yaml` : 원본 지도 메타데이터
- `keepout_mask.pgm` : Nav2 KeepoutFilter용 mask
- `keepout_mask.png` : 확인용 PNG mask
- `keepout_mask.yaml` : keepout mask 메타데이터
- `keepout_overlay_preview.png` : 노란색 주행 가능 영역 확인용 미리보기
- `nav2_params_keepout_addition.yaml` : nav2_params.yaml에 추가할 KeepoutFilter 설정 예시

## mask 의미

현재 생성된 keepout mask는 다음 기준입니다.

- 흰색 영역: 주행 가능 영역
- 검은색 영역: keepout zone, 즉 주행 금지 영역

사용자가 표시한 노란색 영역만 흰색으로 변환했고,
나머지는 모두 검은색 keepout zone으로 처리했습니다.

## 주의

`nav2_params_keepout_addition.yaml`은 그대로 통째로 덮어쓰기보다는,
현재 사용 중인 `nav2_params.yaml`의 `global_costmap`, `local_costmap`,
lifecycle 설정에 병합하는 방식으로 적용하는 것이 안전합니다.
