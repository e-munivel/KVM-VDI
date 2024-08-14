import type { StoryObj } from '@storybook/vue3'
import { LoginProviderForm } from '@/components/login'

const meta = {
  component: LoginProviderForm,
  title: 'LoginProviderForm',
  tags: ['autodocs']
}

export default meta

type Story = StoryObj<typeof meta>

const createStory = (args: any, parameters?: any): Story => ({
  args,
  parameters
})

export const Default = createStory({})
