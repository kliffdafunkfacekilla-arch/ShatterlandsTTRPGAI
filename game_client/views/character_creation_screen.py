# (All imports at top, BUT remove asyncio)import logging# import asyncio <-- REMOVEDfrom kivy.app import App# ... (other Kivy imports)# (Monolith imports are unchanged)# ...# (Asset Loader imports are unchanged)# ...# (Constants are unchanged)# ...# (PortraitButton class is unchanged)# ...class CharacterCreationScreen(Screen):

    # (All properties and __init__ are unchanged)
    # ...

    # --- (build_step_talent is unchanged) ---
def build_step_talent(self):
    self.title_label.text = "Step 5: Choose Ability Talent"
    self.step_ui_container.add_widget(Label(text="Select your starting Talent:"))

    current_choice = self.choices.get('ability_talent')

    self.talent_spinner = Spinner(
        text=current_choice if current_choice else '- Select a Talent -',
        values=self.eligible_talents,
        size_hint_y=None,
        height='44dp'
    )
    self.talent_spinner.option_cls.height = '44dp'
    self.talent_spinner.bind(text=partial(self.select_choice, 'ability_talent'))
    self.step_ui_container.add_widget(self.talent_spinner)

    # This step still calls the fetch function
    self.fetch_eligible_talents() # This call is now synchronous

    # (All other build_step_* functions are unchanged)
    # ...

    # --- REFACTORED: fetch_eligible_talents (now synchronous) ---
    def fetch_eligible_talents(self):
        """
        Calls the rules engine to get talents.
        This is now a SYNCHRONOUS call.
        """
        if not rules_api:
            self.update_talent_spinner([], "Rules API not loaded")
            return

        self.talent_spinner.values = ['Fetching talents...']
        self.talent_spinner.text = 'Fetching talents...'
        self.next_btn.disabled = True

        # Convert skill list to skill rank map
        skill_ranks = {skill: 0 for skill in self.rules_data.get('all_skills_map', {})}
        for skill_name in self.calculated_skills:
            if skill_name in skill_ranks:
                skill_ranks[skill_name] = 1 # All background skills are Rank 1

        payload = {
            "stats": self.calculated_stats,
            "skills": skill_ranks
        }

        # --- THIS IS THE CHANGE ---
        # Remove the async wrapper and call directly
        try:
            # This is now a direct, synchronous call
            talents = rules_api.find_eligible_talents_api(payload)
            self.update_talent_spinner(talents) # Update the UI immediately
        except Exception as e:
            logging.exception(f"Failed to fetch talents: {e}")
            self.update_talent_spinner([], str(e))
    # --- END CHANGE ---

    def update_talent_spinner(self, talents, error_msg=None, *args):
        # (This function is unchanged, but now runs immediately)
        if error_msg: self.eligible_talents = [f'Error: {error_msg}']
        elif not talents: self.eligible_talents = ['- No eligible talents found -']
        else: self.eligible_talents = ['- Select a Talent -'] + [t['name'] for t in talents]

        self.talent_spinner.values = self.eligible_talents
        self.talent_spinner.text = self.eligible_talents[0]
        self.choices['ability_talent'] = None
        self.validate_step()

    # --- REFACTORED: FINAL SUBMISSION (now synchronous) ---

    def submit_character(self):
        """Final step. Validates, builds the schema, and calls the monolith."""
        logging.info("CHAR_CREATE: Submitting character...")
        self.next_btn.disabled = True
        self.next_btn.text = "Creating..."

        # 1. Add the F9 Capstone choice (unchanged)
        final_feature_choices = self.choices['feature_choices']
        final_feature_choices.append({
            "feature_id": "F9",
            "choice_name": self.choices['capstone_choice']
        })

        # 2. Build the Pydantic schema (unchanged)
        try:
            payload = char_schemas.CharacterCreate(
                name=self.choices['name'],
                kingdom=self.choices['kingdom'],
                feature_choices=final_feature_choices,
                origin_choice=self.choices['origin_choice'],
                childhood_choice=self.choices['childhood_choice'],
                coming_of_age_choice=self.choices['coming_of_age_choice'],
                training_choice=self.choices['training_choice'],
                devotion_choice=self.choices['devotion_choice'],
                ability_school=self.choices['ability_school'],
                ability_talent=self.choices['ability_talent'],
                portrait_id=self.choices['portrait_id']
            )
        except Exception as e:
            logging.error(f"Failed to create schema: {e}")
            self.next_btn.text = f"Error: {e}"
            return

        # --- THIS IS THE CHANGE ---
        # 3. Call the monolith service (now synchronous)
        db = None
        try:
            db = CharSession()
            # This is now a direct, synchronous call
            new_char_context = char_services.create_character(
                db=db,
                character=payload,
                rules_data=self.rules_data
            )

            # Call success callback immediately
            self.on_creation_success(new_char_context.name)

        except Exception as e:
            logging.exception("Character creation failed in service.")
            if db: db.rollback()
            # Call failure callback immediately
            self.on_creation_failure(str(e))
        finally:
            if db: db.close()
    # --- END CHANGE ---

    def on_creation_success(self, char_name, *args):
        # (This function is unchanged)
        logging.info(f"Successfully created character: {char_name}")
        App.get_running_app().root.current = 'game_setup'

    def on_creation_failure(self, error_msg, *args):
        # (This function is unchanged)
        logging.error(f"Creation failed: {error_msg}")
        self.next_btn.disabled = False
        self.next_btn.text = "Create Character"
