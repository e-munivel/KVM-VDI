export { default as LoginProviderForm } from './LoginProviderForm.vue'
export { default as LoginProviderExternal } from './LoginProviderExternal.vue'
export { default as LoginCategoriesDropdown } from './LoginCategoriesDropdown.vue'
export { default as LoginCategorySelect } from './LoginCategorySelect.vue'

// TODO: Move this to the correspondant place
export enum Provider {
  SAML = 'saml',
  Google = 'google'
}
