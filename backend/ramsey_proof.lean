import Mathlib

open Classical in
noncomputable example : ∀ (f : Fin 6 → Fin 6 → Prop), (∀ i j, i ≠ j → (f i j ↔ f j i)) →
  (∃ s : Finset (Fin 6), s.card = 3 ∧ (∀ i ∈ s, ∀ j ∈ s, i ≠ j → f i j)) ∨
  (∃ s : Finset (Fin 6), s.card = 3 ∧ (∀ i ∈ s, ∀ j ∈ s, i ≠ j → ¬f i j)) := by
  intro f hsym
  let S := (Finset.univ : Finset (Fin 6)).erase 0
  have hS : S.card = 5 := by native_decide
  let p : Fin 6 → Prop := fun k => f 0 k
  let A := S.filter p
  let B := S.filter (fun k => ¬p k)
  have hAB : A.card + B.card = 5 := by
    change (S.filter p).card + (S.filter (fun k => ¬p k)).card = 5
    rw [Finset.filter_card_add_filter_neg_card_eq_card, hS]
  have h3 : A.card ≥ 3 ∨ B.card ≥ 3 := by omega
  rcases h3 with hA | hB
  · obtain ⟨T, hT_sub, hT_card⟩ := Finset.exists_smaller_set A 3 hA
    by_cases hex : ∃ a ∈ T, ∃ b ∈ T, a ≠ b ∧ f a b
    · obtain ⟨a, ha, b, hb, hab, hfab⟩ := hex
      left
      have ha_f : f 0 a := (Finset.mem_filter.mp (hT_sub ha)).2
      have hb_f : f 0 b := (Finset.mem_filter.mp (hT_sub hb)).2
      have ha_ne0 : a ≠ 0 := by
        intro h; subst h
        exact (Finset.mem_erase.mp (Finset.mem_of_mem_filter _ (hT_sub ha))).1 rfl
      have hb_ne0 : b ≠ 0 := by
        intro h; subst h
        exact (Finset.mem_erase.mp (Finset.mem_of_mem_filter _ (hT_sub hb))).1 rfl
      have ha_f' : f a 0 := (hsym 0 a (Ne.symm ha_ne0)).mp ha_f
      have hb_f' : f b 0 := (hsym 0 b (Ne.symm hb_ne0)).mp hb_f
      have hfba : f b a := (hsym a b hab).mp hfab
      refine ⟨{0, a, b}, ?_, ?_⟩
      · have h1 : (0 : Fin 6) ∉ ({a, b} : Finset (Fin 6)) := by
          simp [ha_ne0.symm, hb_ne0.symm]
        have h2 : a ∉ ({b} : Finset (Fin 6)) := by simp [hab]
        rw [Finset.card_insert_of_not_mem h1, Finset.card_insert_of_not_mem h2,
            Finset.card_singleton]
      · intro i hi j hj hij
        simp only [Finset.mem_insert, Finset.mem_singleton] at hi hj
        rcases hi with rfl | rfl | rfl <;> rcases hj with rfl | rfl | rfl
        · exact absurd rfl hij
        · exact ha_f
        · exact hb_f
        · exact ha_f'
        · exact absurd rfl hij
        · exact hfab
        · exact hb_f'
        · exact hfba
        · exact absurd rfl hij
    · right
      push_neg at hex
      exact ⟨T, hT_card, fun a ha b hb hab => hex a ha b hb hab⟩
  · obtain ⟨T, hT_sub, hT_card⟩ := Finset.exists_smaller_set B 3 hB
    by_cases hex : ∃ a ∈ T, ∃ b ∈ T, a ≠ b ∧ ¬f a b
    · obtain ⟨a, ha, b, hb, hab, hfab⟩ := hex
      right
      have ha_nf : ¬f 0 a := (Finset.mem_filter.mp (hT_sub ha)).2
      have hb_nf : ¬f 0 b := (Finset.mem_filter.mp (hT_sub hb)).2
      have ha_ne0 : a ≠ 0 := by
        intro h; subst h
        exact (Finset.mem_erase.mp (Finset.mem_of_mem_filter _ (hT_sub ha))).1 rfl
      have hb_ne0 : b ≠ 0 := by
        intro h; subst h
        exact (Finset.mem_erase.mp (Finset.mem_of_mem_filter _ (hT_sub hb))).1 rfl
      have ha_nf' : ¬f a 0 := fun h => ha_nf ((hsym 0 a (Ne.symm ha_ne0)).mpr h)
      have hb_nf' : ¬f b 0 := fun h => hb_nf ((hsym 0 b (Ne.symm hb_ne0)).mpr h)
      have hfnba : ¬f b a := fun h => hfab ((hsym a b hab).mpr h)
      refine ⟨{0, a, b}, ?_, ?_⟩
      · have h1 : (0 : Fin 6) ∉ ({a, b} : Finset (Fin 6)) := by
          simp [ha_ne0.symm, hb_ne0.symm]
        have h2 : a ∉ ({b} : Finset (Fin 6)) := by simp [hab]
        rw [Finset.card_insert_of_not_mem h1, Finset.card_insert_of_not_mem h2,
            Finset.card_singleton]
      · intro i hi j hj hij
        simp only [Finset.mem_insert, Finset.mem_singleton] at hi hj
        rcases hi with rfl | rfl | rfl <;> rcases hj with rfl | rfl | rfl
        · exact absurd rfl hij
        · exact ha_nf
        · exact hb_nf
        · exact ha_nf'
        · exact absurd rfl hij
        · exact hfab
        · exact hb_nf'
        · exact hfnba
        · exact absurd rfl hij
    · left
      push_neg at hex
      exact ⟨T, hT_card, fun a ha b hb hab => hex a ha b hb hab⟩
