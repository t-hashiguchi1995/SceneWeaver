import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, loadStudioContext, saveStudioContext } from '../../lib/api'

export const Route = createFileRoute('/characters/')({
  component: CharactersPage,
})

function CharactersPage() {
  const { t } = useTranslation(['character', 'common'])
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [activeId, setActiveId] = useState(() => loadStudioContext().characterId ?? '')
  const [activeName, setActiveName] = useState(() => loadStudioContext().characterName ?? '')
  const characters = useQuery({ queryKey: ['characters'], queryFn: api.listCharacters })

  const useInStudio = (characterId: string, characterName: string) => {
    saveStudioContext({ characterId, characterName })
    setActiveId(characterId)
    setActiveName(characterName)
    void navigate({ to: '/story' })
  }

  const create = useMutation({
    mutationFn: () => api.createCharacter(name.trim()),
    onSuccess: async (created) => {
      setName('')
      await qc.invalidateQueries({ queryKey: ['characters'] })
      useInStudio(created.id, created.display_name)
    },
  })

  return (
    <section className="page" data-testid="characters-page">
      <h1>{t('character:title')}</h1>
      <p className="lede">{t('character:lede')}</p>
      {activeId && (
        <p className="meta" data-testid="character-active-banner">
          {t('character:activeBanner', { name: activeName || activeId.slice(0, 8) })}
        </p>
      )}
      <form
        className="inline-form"
        onSubmit={(e) => {
          e.preventDefault()
          if (name.trim()) create.mutate()
        }}
      >
        <input
          data-testid="character-name-input"
          aria-label={t('character:nameAria')}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('character:namePlaceholder')}
        />
        <button
          type="submit"
          className="btn primary"
          data-testid="character-create"
          disabled={create.isPending}
        >
          {t('common:actions.create')}
        </button>
      </form>
      <ul className="list" data-testid="character-list">
        {(characters.data ?? []).map((c) => (
          <li key={c.id} data-testid="character-item">
            <strong>{c.display_name}</strong>
            <span className="meta">{c.id.slice(0, 8)}…</span>
            <button
              type="button"
              className={activeId === c.id ? 'btn primary' : 'btn'}
              data-testid={`character-use-${c.id}`}
              onClick={() => useInStudio(c.id, c.display_name)}
            >
              {activeId === c.id ? t('character:openStory') : t('character:useInStudio')}
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
