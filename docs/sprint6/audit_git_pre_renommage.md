● Bash(git branch -vv)                                                                   
  ⎿  * feat/sprint2-image-pipeline b1d78ab [origin/feat/sprint2-image-pipeline: en a
     vance de 3] T11 sprint 5: clôture sprint 5 — audit intent matching + kickoff sp     
     rint 6                              
     … +8 lines (ctrl+o to expand)                                                       
                                                                                         
● Bash(git branch -r)
  ⎿    origin/HEAD -> origin/cognitive-pipeline-refactor                                 
       origin/cognitive-pipeline-refactor
       origin/feat/sprint2-image-pipeline 
       origin/main
                                                                                         
● Bash(git remote show origin)
  ⎿  * distant origin                                                                    
       URL de rapatriement : https://github.com/cossonn-coder/aria.git
       URL push : https://github.com/cossonn-coder/aria.git
     … +14 lines (ctrl+o to expand)
                                                                                         
● Bash(git log @{u}.. --oneline)
  ⎿  b1d78ab T11 sprint 5: clôture sprint 5 — audit intent matching + kickoff sprint     
      6           
     3b57136 T3 sprint 5: cache négatif providers LLM (dette #8)
     b0aaee5 T2 sprint 5: fix classifier cache (dette #20)
                                                                                         
● Bash(git worktree list)
  ⎿  /home/nico/Nextcloud/projects/aria  b1d78ab [feat/sprint2-image-pipeline]           
                  
● Bash(git stash list)                          
  ⎿  (No output)
                                                                                         
● Bash(git reflog -10)                          
  ⎿  b1d78ab HEAD@{0}: commit: T11 sprint 5: clôture sprint 5 — audit intent matchin     
     g + kickoff sprint 6                                                                
     3b57136 HEAD@{1}: commit: T3 sprint 5: cache négatif providers LLM (dette #8)
     … +14 lines (ctrl+o to expand)                                                      
                                                                                         
● Bash(git fetch --dry-run 2>&1)                
  ⎿  (No output)                                                                         
                                                                                         
● Bash(git tag --sort=-creatordate | head -20)
  ⎿  sprint-5                                                                            
     sprint-2                                                                            
     sprint-4                  
     … +3 lines (ctrl+o to expand)                                                       
                                                                                         
● Bash(git log main --oneline -5)          
  ⎿  19dae68 fix: pipeline cognitif strict + stabilité tests -analyst_agent: supprim     
     e retrieve_by_intent direct (0.2) - kernel: injecte session_memory dans AgentCo     
     ntext (0.2) - controller : trace cognitive + halted check - intent_recall_engin
     … +9 lines (ctrl+o to expand)                                                       
                                                                                         
● Bash(git log feat/sprint2-image-pipeline..main --oneline)
  ⎿  (No output)                                                                         
                                                                                         
● Bash(git log main..feat/sprint2-image-pipeline --oneline | head -30)
  ⎿  b1d78ab T11 sprint 5: clôture sprint 5 — audit intent matching + kickoff sprint     
      6                                                                                  
     3b57136 T3 sprint 5: cache négatif providers LLM (dette #8)
     … +25 lines (ctrl+o to expand)                                                      
                                                                                         
● Bash(git branch -a | grep -i develop)          
  ⎿  No matches found                                                                    
                                                                                         
● Bash(git merge-base main feat/sprint2-image-pipeline)
  ⎿  19dae68583a1aef2eb4dbe16d0baaf5af1731c7b                                            
                                                                                         
● Bash(for t in sprint-5 sprint-4 sprint-3.1 sprint-3 sprint-2 aria-kernel-0.2; do echo
      -n "$t: "; git ls-remote --tags origin "refs/tags/$t" 2>/dev/null | awk '{print…)  
  ⎿  sprint-5: sprint-4: refs/tags/sprint-4                                              
     sprint-3.1: refs/tags/sprint-3.1
     sprint-3: refs/tags/sprint-3                                                        
     … +2 lines (ctrl+o to expand)
             
● Bash(git log main --oneline --all --source 2>/dev/null | head -3; echo "---"; git   
      rev-list --count main)                                                             
  ⎿  b1d78ab    refs/heads/feat/sprint2-image-pipeline T11 sprint 5: clôture sprint 5 —
     audit intent matching + kickoff sprint 6                                            
     3b57136    refs/heads/feat/sprint2-image-pipeline T3 sprint 5: cache négatif provid
     … +5 lines (ctrl+o to expand)                                                       
                                                                                         
                                                                                       
● Audit git — état pré-renommage (lecture seule)                                         
                                                                                         
  Branches                                                                               
                                                                                         
  Branche: feat/sprint2-image-pipeline                                                   
  Locale: ✅ (HEAD b1d78ab)                                                              
  Remote: ✅                                                                             
  Tracking: suit origin/feat/sprint2-image-pipeline
  État: +3 commits non pushés
  ────────────────────────────────────────                                               
  Branche: main                                                                          
  Locale: ✅ (HEAD 19dae68)                                                              
  Remote: ✅                                                                             
  Tracking: suit origin/main, à jour
  État: existe déjà — 7 commits totaux
  ────────────────────────────────────────
  Branche: cognitive-pipeline-refactor                                                   
  Locale: ❌
  Remote: ✅                                                                             
  Tracking: —     
  État: branche par défaut côté origin (HEAD)
  ────────────────────────────────────────
  Branche: develop                                                                       
  Locale: ❌
  Remote: ❌                                                                             
  Tracking: —     
  État: n'existe nulle part

  État de main

  - 7 commits totaux, contenu : essentiellement requirements.txt + un commit fix:        
  pipeline cognitif strict… (19dae68).
  - git log feat/sprint2-image-pipeline..main = vide → main n'a rien de plus que la feat 
  branch.                                                                                
  - merge-base main feat/sprint2-image-pipeline = 19dae68 = HEAD de main → main est un 
  ancêtre strict de la feat branch (la feat branch est ~30 commits devant).              
  - main n'est donc pas orpheline ni placeholder, mais c'est une branche stagnante : le
  travail réel a divergé sur cognitive-pipeline-refactor puis                            
  feat/sprint2-image-pipeline. La HEAD remote pointe d'ailleurs sur
  cognitive-pipeline-refactor, pas sur main.                                             
                  
  Commits non pushés (sur branche courante)

  3 commits sprint 5, en avance sur origin/feat/sprint2-image-pipeline :                 
  - b1d78ab T11 — clôture sprint 5
  - 3b57136 T3 — cache négatif LLM                                                       
  - b0aaee5 T2 — fix classifier cache
                                                                                         
  Tags non pushés                                                                        
   
  - sprint-5 : local uniquement, absent de origin.                                       
  - sprint-2, sprint-3, sprint-3.1, sprint-4, aria-kernel-0.2 : tous pushés.
                                                                                         
  Reste                                                                                  
                                                                                         
  - Worktrees : un seul (le repo principal).                                             
  - Stash : vide. 
  - Reflog : propre, aucun rebase/reset récent.                                          
  - git fetch --dry-run : aucun changement remote à récupérer.                           
                                                                                         
  ---                                                                                    
  Réponses aux questions clés                                                            
                             
  (a) main est-elle dispo comme nom de branche cible ?
  NON. main existe déjà — locale + remote. Renommer feat/sprint2-image-pipeline → main   
  exigerait soit la suppression préalable de main (locale + remote), soit un fast-forward
   de main (qui est ancêtre strict de la feat branch, donc faisable proprement) plutôt   
  qu'un renommage.                                                                       
                  
  (b) Risques sur le renommage
  1. Collision de nom main — bloquant tant que main n'est pas traité.
  2. 3 commits non pushés sur la branche courante — à pusher avant tout renommage pour ne
   pas perdre la chaîne T11/T3/T2.                                                       
  3. Tag sprint-5 local uniquement — à pusher (git push origin sprint-5) sinon il restera
   orphelin si la branche est renommée/supprimée.                                        
  4. HEAD remote = cognitive-pipeline-refactor — si la cible finale est de faire de la   
  feat branch la nouvelle branche par défaut, il faudra basculer la HEAD origin (côté 
  GitHub : "default branch" dans les settings) après le push.                            
  5. cognitive-pipeline-refactor côté remote — pas de copie locale ; à clarifier en T-Z2
  si on la conserve, l'archive ou la supprime.                                           
                                                                                         
  Aucun stash, worktree ou ref orpheline ne complique l'opération. La voie la plus propre
   reste à arbitrer en T-Z2.    