/**
 * Which persisted keys are machine-level UI preferences (#145213).
 *
 * Only these leave localStorage for the machine's shared store, so native
 * Desktop and every browser that opens this machine's Webapp show the same
 * choices. Scoped families keep their scope inside the key name (a
 * `….profile.<name>` or per-connection suffix): only the location changes.
 *
 * Deliberately NOT here (they stay in this browser/window):
 * - credentials, grants and connection config: gateway registry, custom model
 *   endpoints, plugin decisions and preview-script grants, embed permissions;
 * - per-window or per-device runtime state: layout tree, open tiles and tabs,
 *   last route/session, scroll, zoom, pet and popout geometry, keep-awake;
 * - drafts, queues, journals and caches: composer queue, in-flight turns,
 *   pending/prepared submissions, previews, pricing, backend skin cache, the
 *   "provider configured" onboarding cache (each backend answers that itself);
 * - one-off notices: butterbar, update and real-profile prompts.
 */

const SHARED_KEYS: ReadonlySet<string> = new Set([
  // Appearance.
  'hermes-desktop-theme-v2',
  'hermes-desktop-mode-v1',
  'hermes-desktop-profile-themes-v1',
  'hermes-desktop-profile-modes-v1',
  'hermes-desktop-user-themes-v1',
  'lattice.desktop.backdrop.v1',
  'lattice.desktop.chat-text-scale.v1',
  'lattice.desktop.interfaceMode.v1',
  'lattice.desktop.textDirection',
  'lattice.desktop.translucency.v2',
  'lattice.desktop.user-bubble-transparency.v1',
  // Sessions sidebar and profile rail.
  'lattice.desktop.agentsGroupedByWorkspace',
  'lattice.desktop.profileColors',
  'lattice.desktop.profileOrder',
  'lattice.desktop.profileRailVisible',
  'lattice.desktop.sessionListDensity',
  'lattice.desktop.sessionOrder',
  'lattice.desktop.sessionOrder.manual',
  'lattice.desktop.showAllProfiles',
  'lattice.desktop.sidebarAgentsGrouped.allProfiles',
  'lattice.desktop.sidebarCardRows',
  'lattice.desktop.sidebarGrouping',
  'lattice.desktop.sidebarGrouping.allProfiles',
  'lattice.desktop.sidebarRowMeta',
  'lattice.desktop.sidebarShowAllSessions',
  'lattice.desktop.sidebarShowArchived',
  'lattice.desktop.sidebarSortKey',
  // Status bar.
  'lattice.desktop.statusbarHidden.v2',
  'lattice.desktop.statusbarVisible.v2',
  // Transcript and tools.
  'lattice.desktop.hideThreadTimeline',
  'lattice.desktop.reasoning.collapsedByDefault',
  'lattice.desktop.toolView.hideCodeDiffs',
  'lattice.desktop.toolView.technical',
  // Shell, panes and behaviour.
  'lattice.desktop.alwaysExternalLinks.v1',
  'lattice.desktop.capabilities.catalogCardView',
  'lattice.desktop.composerPopout.enabled',
  'lattice.desktop.composerPopout.gesturesEnabled',
  'lattice.desktop.files.showIgnored',
  'lattice.desktop.keybinds',
  'lattice.desktop.layoutPresets.v2',
  'lattice.desktop.panesFlipped',
  'lattice.desktop.tabStripDefault',
  'lattice.desktop.titlebarAppActions',
  // Guidance: what the user already skipped, saw or dismissed does not come
  // back in every new browser or origin (#145600).
  'hermes-onboarding-skipped-v1',
  'lattice.desktop.tips.last.v1',
  'lattice.desktop.tips.next.v1',
  'lattice.desktop.tips.retired.v1',
  'lattice.desktop.tips.rotation.v1',
  'lattice.desktop.tips.shownAt.v1',
  'lattice.desktop.tours.v1',
  // Sound and media.
  'lattice.desktop.autoSpeakReplies',
  'lattice.desktop.completionSoundVariantId',
  'lattice.desktop.hapticsMuted',
  'lattice.desktop.videoPlaybackSpeed',
  // Model picker.
  'lattice.desktop.collapsed-providers',
  'lattice.desktop.favorite-models',
  // visible-models is a diff against known-models: they only make sense together.
  'lattice.desktop.known-models',
  'lattice.desktop.model-presets',
  'lattice.desktop.visible-models'
])

/** Families whose scope rides in the key suffix (gateway aliases/order/collapsed). */
const SHARED_PREFIXES: readonly string[] = ['lattice.desktop.sidebar.gatewayGroups.v1.']

export function isSharedPreferenceKey(key: string): boolean {
  return SHARED_KEYS.has(key) || SHARED_PREFIXES.some(prefix => key.startsWith(prefix))
}
