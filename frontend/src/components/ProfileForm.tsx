import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface FormData {
  height: string;
  weight: string;
  age: string;
  primaryGoal: string;
  specificGoals: string;
  fitnessLevel: string;
  activityLevel: string;
  workoutPreference: string;
  workoutDays: number;
  workoutDuration: string;
  availableEquipment: string[];
  previousInjuries: string;
  currentInjuries: string;
  dietaryPreferences: string;
  allergies: string;
  foodRestrictions: string;
  mealsPerDay: number;
  cookingSkill: string;
  budget: string;
  sleepHours: number;
  sleepQuality: string;
  stressLevel: number;
  waterIntake: number;
  smokingStatus: string;
  alcoholConsumption: string;
  medicationsSupplements: string;
  chronicConditions: string;
  inbodyFile: File | null;
  medicalReports: File | null;
}

interface ProfileFormProps {
  onSave: () => void;
  userId: number;
}

const ProfileForm: React.FC<ProfileFormProps> = ({ onSave, userId }) => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const [formData, setFormData] = useState<FormData>({
    height: '',
    weight: '',
    age: '',
    primaryGoal: '',
    specificGoals: '',
    fitnessLevel: 'beginner',
    activityLevel: 'sedentary',
    workoutPreference: 'home',
    workoutDays: 3,
    workoutDuration: '30-45',
    availableEquipment: [],
    previousInjuries: '',
    currentInjuries: '',
    dietaryPreferences: 'balanced',
    allergies: '',
    foodRestrictions: '',
    mealsPerDay: 3,
    cookingSkill: 'intermediate',
    budget: 'moderate',
    sleepHours: 7,
    sleepQuality: 'good',
    stressLevel: 5,
    waterIntake: 2,
    smokingStatus: 'never',
    alcoholConsumption: 'occasional',
    medicationsSupplements: '',
    chronicConditions: '',
    inbodyFile: null,
    medicalReports: null,
  });

  const calculateBMI = () => {
    const heightM = parseFloat(formData.height) / 100;
    const weightKg = parseFloat(formData.weight);
    if (heightM && weightKg) {
      return (weightKg / (heightM * heightM)).toFixed(1);
    }
    return '';
  };

  const getBMICategory = (bmi: number) => {
    if (bmi < 18.5) return 'Underweight';
    if (bmi < 25) return 'Normal weight';
    if (bmi < 30) return 'Overweight';
    return 'Obese';
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checkbox = e.target as HTMLInputElement;
      const equipmentList = [...formData.availableEquipment];
      if (checkbox.checked) {
        equipmentList.push(value);
      } else {
        const index = equipmentList.indexOf(value);
        if (index > -1) {
          equipmentList.splice(index, 1);
        }
      }
      setFormData({ ...formData, availableEquipment: equipmentList });
    } else {
      setFormData({ ...formData, [name]: value });
    }
    
    if (message) setMessage('');
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, files } = e.target;
    if (files && files[0]) {
      setFormData({ ...formData, [name]: files[0] });
    }
  };

  const validateStep = (step: number) => {
    switch (step) {
      case 1:
        if (!formData.height || parseFloat(formData.height) < 100 || parseFloat(formData.height) > 250) {
          return 'Please enter a valid height (100-250 cm)';
        }
        if (!formData.weight || parseFloat(formData.weight) < 30 || parseFloat(formData.weight) > 300) {
          return 'Please enter a valid weight (30-300 kg)';
        }
        if (!formData.age || parseInt(formData.age) < 13 || parseInt(formData.age) > 100) {
          return 'Please enter a valid age (13-100 years)';
        }
        break;
      case 2:
        if (!formData.primaryGoal) return 'Please select a primary goal';
        if (!formData.specificGoals.trim()) return 'Please describe your specific goals';
        break;
      case 3:
        break;
      case 4:
        break;
      case 5:
        if (formData.sleepHours < 3 || formData.sleepHours > 12) {
          return 'Please enter valid sleep hours (3-12)';
        }
        if (formData.stressLevel < 1 || formData.stressLevel > 10) {
          return 'Please rate stress level between 1-10';
        }
        if (formData.waterIntake < 0.5 || formData.waterIntake > 5) {
          return 'Please enter valid water intake (0.5-5 liters)';
        }
        break;
      case 6:
        if (!formData.inbodyFile) return 'Please upload your InBody picture';
        break;
    }
    return null;
  };

  const nextStep = () => {
    const error = validateStep(currentStep);
    if (error) {
      setMessage(error);
      return;
    }
    setMessage('');
    setCurrentStep(prev => Math.min(prev + 1, 6));
  };

  const prevStep = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1));
    setMessage('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const finalValidation = validateStep(6);
    if (finalValidation) {
      setMessage(finalValidation);
      return;
    }

    setIsLoading(true);
    setMessage('');

    const formDataToSend = new FormData();
    
    Object.entries(formData).forEach(([key, value]) => {
      if (key === 'availableEquipment') {
        formDataToSend.append(key, JSON.stringify(value));
      } else if (key === 'inbodyFile' || key === 'medicalReports') {
        if (value) {
          formDataToSend.append(key, value as File);
        }
      } else {
        formDataToSend.append(key, String(value));
      }
    });
    
    formDataToSend.append('user_id', userId.toString());
    formDataToSend.append('bmi', calculateBMI());

    try {
      const response = await axios.post('http://localhost:5000/api/profile', formDataToSend, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
      });
      
      setMessage(response.data.message);
      onSave();
    } catch (error: any) {
      console.error('Profile submission error:', error);
      if (error.code === 'ECONNABORTED') {
        setMessage('Request timeout. Please try again.');
      } else if (error.response) {
        setMessage(error.response.data.error || 'Failed to save profile. Please try again.');
      } else {
        setMessage('Unable to connect to server. Please check your connection.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const equipmentOptions = [
    'Dumbbells', 'Barbells', 'Resistance Bands', 'Kettlebells', 'Pull-up Bar',
    'Yoga Mat', 'Treadmill', 'Stationary Bike', 'Rowing Machine', 'None'
  ];

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Personal Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Height (cm) *</label>
                <input
                  type="number"
                  name="height"
                  value={formData.height}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="170"
                  min="100"
                  max="250"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Weight (kg) *</label>
                <input
                  type="number"
                  name="weight"
                  value={formData.weight}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  placeholder="70"
                  min="30"
                  max="300"
                  step="0.1"
                  required
                />
              </div>
            </div>
            {formData.height && formData.weight && (
              <div className="bg-blue-50 p-4 rounded-md">
                <p className="text-sm text-blue-800">
                  <strong>BMI:</strong> {calculateBMI()} - {getBMICategory(parseFloat(calculateBMI()))}
                </p>
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Age *</label>
              <input
                type="number"
                name="age"
                value={formData.age}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                min="13"
                max="100"
                required
              />
            </div>
          </div>
        );
      case 2:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Your Goals</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Primary Goal *</label>
              <select
                name="primaryGoal"
                value={formData.primaryGoal}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                required
              >
                <option value="">Select your primary goal</option>
                <option value="weight_loss">Weight Loss</option>
                <option value="weight_gain">Weight Gain</option>
                <option value="muscle_building">Muscle Building</option>
                <option value="maintain_weight">Maintain Current Weight</option>
                <option value="improve_fitness">Improve Overall Fitness</option>
                <option value="improve_health">Improve Health Conditions</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Specific Goals & Motivation *</label>
              <textarea
                name="specificGoals"
                value={formData.specificGoals}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                rows={4}
                placeholder="Describe your specific goals, timeline, and what motivates you..."
                required
              />
            </div>
          </div>
        );
      case 3:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Fitness Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Fitness Level</label>
                <select
                  name="fitnessLevel"
                  value={formData.fitnessLevel}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="no_experience">No Experience</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Current Activity Level</label>
                <select
                  name="activityLevel"
                  value={formData.activityLevel}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="sedentary">Sedentary</option>
                  <option value="lightly_active">Lightly Active</option>
                  <option value="moderately_active">Moderately Active</option>
                  <option value="very_active">Very Active</option>
                  <option value="extremely_active">Extremely Active</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Workout Preference</label>
                <select
                  name="workoutPreference"
                  value={formData.workoutPreference}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="home">Home Workout</option>
                  <option value="gym">Gym Workout</option>
                  <option value="outdoor">Outdoor Activities</option>
                  <option value="mixed">Mixed</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Workout Days Per Week</label>
                <input
                  type="number"
                  name="workoutDays"
                  value={formData.workoutDays}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="7"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Preferred Workout Duration</label>
              <select
                name="workoutDuration"
                value={formData.workoutDuration}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="15-30">15-30 minutes</option>
                <option value="30-45">30-45 minutes</option>
                <option value="45-60">45-60 minutes</option>
                <option value="60+">60+ minutes</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Available Equipment</label>
              <div className="grid grid-cols-2 gap-2">
                {['Dumbbells', 'Barbells', 'Resistance Bands', 'Kettlebells', 'Pull-up Bar', 'Yoga Mat', 'Treadmill', 'Stationary Bike', 'Rowing Machine', 'None'].map((equipment) => (
                  <label key={equipment} className="flex items-center">
                    <input
                      type="checkbox"
                      value={equipment}
                      checked={formData.availableEquipment.includes(equipment)}
                      onChange={handleChange}
                      className="mr-2"
                    />
                    <span className="text-sm">{equipment}</span>
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Previous Injuries</label>
              <textarea
                name="previousInjuries"
                value={formData.previousInjuries}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                placeholder="List any previous injuries..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Injuries or Limitations</label>
              <textarea
                name="currentInjuries"
                value={formData.currentInjuries}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                placeholder="Any current injuries or limitations..."
              />
            </div>
          </div>
        );
      case 4:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Nutrition Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dietary Preference</label>
                <select
                  name="dietaryPreferences"
                  value={formData.dietaryPreferences}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="balanced">Balanced Diet</option>
                  <option value="vegetarian">Vegetarian</option>
                  <option value="vegan">Vegan</option>
                  <option value="keto">Keto</option>
                  <option value="paleo">Paleo</option>
                  <option value="mediterranean">Mediterranean</option>
                  <option value="low_carb">Low Carb</option>
                  <option value="high_protein">High Protein</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Meals Per Day</label>
                <select
                  name="mealsPerDay"
                  value={formData.mealsPerDay}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value={2}>2 meals</option>
                  <option value={3}>3 meals</option>
                  <option value={4}>4 meals</option>
                  <option value={5}>5 meals</option>
                  <option value={6}>6 meals</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Food Allergies</label>
              <textarea
                name="allergies"
                value={formData.allergies}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                placeholder="List any food allergies..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Food Restrictions or Dislikes</label>
              <textarea
                name="foodRestrictions"
                value={formData.foodRestrictions}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                placeholder="Foods you avoid or dislike..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Cooking Skill Level</label>
                <select
                  name="cookingSkill"
                  value={formData.cookingSkill}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Food Budget</label>
                <select
                  name="budget"
                  value={formData.budget}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="low">Low Budget</option>
                  <option value="moderate">Moderate Budget</option>
                  <option value="high">High Budget</option>
                </select>
              </div>
            </div>
          </div>
        );
      case 5:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Health & Lifestyle</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sleep Hours Per Night</label>
                <input
                  type="number"
                  name="sleepHours"
                  value={formData.sleepHours}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  min="3"
                  max="12"
                  step="0.5"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Sleep Quality</label>
                <select
                  name="sleepQuality"
                  value={formData.sleepQuality}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="poor">Poor</option>
                  <option value="fair">Fair</option>
                  <option value="good">Good</option>
                  <option value="excellent">Excellent</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Stress Level (1-10)</label>
                <input
                  type="range"
                  name="stressLevel"
                  value={formData.stressLevel}
                  onChange={handleChange}
                  className="w-full"
                  min="1"
                  max="10"
                />
                <div className="flex justify-between text-xs text-gray-500">
                  <span>Low (1)</span>
                  <span className="font-medium">{formData.stressLevel}</span>
                  <span>High (10)</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Daily Water Intake (Liters)</label>
                <input
                  type="number"
                  name="waterIntake"
                  value={formData.waterIntake}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                  min="0.5"
                  max="5"
                  step="0.5"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Smoking Status</label>
                <select
                  name="smokingStatus"
                  value={formData.smokingStatus}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="never">Never</option>
                  <option value="former">Former</option>
                  <option value="occasional">Occasional</option>
                  <option value="regular">Regular</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alcohol Consumption</label>
                <select
                  name="alcoholConsumption"
                  value={formData.alcoholConsumption}
                  onChange={handleChange}
                  className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="never">Never</option>
                  <option value="occasional">Occasional</option>
                  <option value="moderate">Moderate</option>
                  <option value="regular">Regular</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Current Medications or Supplements</label>
              <textarea
                name="medicationsSupplements"
                value={formData.medicationsSupplements}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                placeholder="List any medications or supplements..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Chronic Conditions or Health Issues</label>
              <textarea
                name="chronicConditions"
                value={formData.chronicConditions}
                onChange={handleChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                rows={2}
                placeholder="Any chronic conditions or health issues..."
              />
            </div>
          </div>
        );
      case 6:
        return (
          <div className="space-y-6">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Upload Files & Review</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">InBody Picture *</label>
              <input
                type="file"
                name="inbodyFile"
                accept="image/*"
                onChange={handleFileChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Medical Reports (Optional)</label>
              <input
                type="file"
                name="medicalReports"
                accept="application/pdf,image/*"
                onChange={handleFileChange}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="bg-gray-50 p-4 rounded-md">
              <h4 className="text-lg font-medium text-gray-900 mb-2">Summary</h4>
              <p><strong>BMI:</strong> {calculateBMI()} - {getBMICategory(parseFloat(calculateBMI()))}</p>
              <p><strong>Primary Goal:</strong> {formData.primaryGoal}</p>
              <p><strong>Fitness Level:</strong> {formData.fitnessLevel}</p>
              <p><strong>Dietary Preference:</strong> {formData.dietaryPreferences}</p>
              <p><strong>Sleep Hours:</strong> {formData.sleepHours}</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-100 to-white flex items-center justify-center p-4">
      <div className="bg-white p-8 rounded-lg shadow-lg w-full max-w-2xl">
        <h2 className="text-3xl font-bold text-green-600 mb-6 text-center">Complete Your Profile 📋</h2>
        {message && (
          <div className={`text-center p-3 rounded-md mb-4 ${message.includes('error') || message.includes('invalid') || message.includes('failed')
            ? 'bg-red-100 text-red-700 border border-red-300'
            : 'bg-green-100 text-green-700 border border-green-300'
          }`}>
            {message}
          </div>
        )}
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600">
            {Array.from({ length: 6 }, (_, i) => (
              <span key={i} className={`w-1/6 text-center ${currentStep > i + 1 ? 'text-green-600' : currentStep === i + 1 ? 'text-blue-600' : 'text-gray-400'}`}>
                Step {i + 1}
              </span>
            ))}
          </div>
          <progress className="w-full h-2 bg-gray-200 rounded-full mt-2" value={currentStep} max="6"></progress>
        </div>
        <form onSubmit={handleSubmit} className="space-y-6">
          {renderStep()}
          <div className="flex justify-between">
            {currentStep > 1 && (
              <button
                type="button"
                onClick={prevStep}
                className="px-4 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400 transition"
                disabled={isLoading}
              >
                Previous
              </button>
            )}
            {currentStep < 6 ? (
              <button
                type="button"
                onClick={nextStep}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition ml-auto"
                disabled={isLoading}
              >
                Next
              </button>
            ) : (
              <button
                type="submit"
                disabled={isLoading}
                className={`px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition ml-auto ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                {isLoading ? 'Submitting...' : 'Submit & Get Recommendations 🚀'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileForm;