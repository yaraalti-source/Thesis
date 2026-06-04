<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends \Illuminate\Database\Eloquent\Factories\Factory<\App\Models\Translation>
 */
class TranslationFactory extends Factory
{
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'user_id' => \App\Models\User::factory(), // Create a related user
            'input_type' => $this->faker->randomElement(['video', 'image', 'live']),
            'input_data' => $this->faker->filePath(), // Random file path
            'created_at' => now(),
            'updated_at' => now(),
        ];
    }
}
